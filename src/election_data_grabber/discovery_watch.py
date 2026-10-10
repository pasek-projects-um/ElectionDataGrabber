"""Repeatable discovery watches; changes never certify service or live results."""

from __future__ import annotations

import hashlib
import json
import re
import time
from collections import Counter, defaultdict
from urllib.parse import urlsplit, urlunsplit
from urllib.robotparser import RobotFileParser

import httpx

from election_data_grabber.authority_directory import extract_directory
from election_data_grabber.discovery_publication import clean_public_candidate, publishable_url
from election_data_grabber.national_discovery import (
    ArtifactNeedsInspection,
    Fetcher,
    RequestBudgetExhausted,
    discover,
    html_access_state,
    load_catalog,
    normalize,
    save,
)

USER_AGENT = "ElectionDataGrabber"
ARTIFACT_PATH = re.compile(r"\.(pdf|csv|xlsx?|xml|json|zip|js|css)$", re.IGNORECASE)


class RobotsUnavailable(ValueError):
    pass


class RobotsDenied(ValueError):
    pass


class WatchFetcher(Fetcher):
    """Apply robots rules and the shared request budget before fetching a page."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.robots = {}

    def check_robots(self, url):
        parsed = urlsplit(url)
        origin = urlunsplit((parsed.scheme, parsed.netloc, "", "", ""))
        if origin not in self.robots:
            if self.remaining <= 0:
                raise RequestBudgetExhausted()
            self.remaining -= 1
            self.requests += 1
            host = parsed.hostname
            time.sleep(max(0, self.delay - (time.monotonic() - self.last.get(host, 0))))
            self.last[host] = time.monotonic()
            with self.client.stream("GET", origin + "/robots.txt") as response:
                if response.status_code == 404:
                    self.robots[origin] = None
                elif response.status_code in (401, 403):
                    raise RobotsDenied()
                elif response.status_code != 200:
                    raise RobotsUnavailable("Robots response unresolved")
                else:
                    data = bytearray()
                    for chunk in response.iter_bytes():
                        data.extend(chunk)
                        if len(data) > 256_000:
                            raise RobotsUnavailable("Robots response exceeds byte limit")
                    if "html" in response.headers.get("content-type", "").lower():
                        raise RobotsUnavailable("Robots returned HTML")
                    text = data.decode("utf-8", errors="replace")
                    if text.lstrip().lower().startswith(("<!doctype html", "<html")):
                        raise RobotsUnavailable("Robots returned HTML")
                    parser = RobotFileParser()
                    parser.parse(text.splitlines())
                    self.robots[origin] = parser
        parser = self.robots[origin]
        if parser is not None:
            if not parser.can_fetch(USER_AGENT, url):
                raise RobotsDenied()
            delay = parser.crawl_delay(USER_AGENT)
            if delay is not None:
                self.delay = max(self.delay, delay)

    def before_request(self, url):
        self.check_robots(url)


def seed_groups(seeds):
    groups = defaultdict(list)
    for seed in seeds:
        url = normalize(seed.get("url", ""))
        if url and publishable_url(url):
            groups[url].append(seed)
    return groups


def follow_candidates(seeds, state, max_depth):
    """Follow observed HTML candidates on later passes, bounded by graph depth."""
    followed = list(seeds)
    for candidate in state.get("candidates", {}).values():
        depth = candidate.get("watch_depth", 1)
        if depth > max_depth or ARTIFACT_PATH.search(urlsplit(candidate["url"]).path):
            continue
        associations = candidate.get("seed_associations", []) or [{}]
        for association in associations:
            followed.append({"url": candidate["url"], "watch_depth": depth,
                             "states": association.get("states", ""),
                             "associated_unit_ids": association.get("associated_unit_ids", "")})
    return followed


def choose_due(groups, pages, now, limit):
    """Oldest/unvisited first, with a state round-robin rather than URL prefix bias."""
    by_state = defaultdict(list)
    for url, seeds in groups.items():
        page = pages.get(url, {})
        if page.get("next_check_at", 0) <= now:
            states = {s.strip() for seed in seeds for s in seed.get("states", seed.get("state", "")).split("|")
                      if s.strip()}
            by_state[min(states, default="").strip()].append(url)
    for urls in by_state.values():
        urls.sort(key=lambda url: (pages.get(url, {}).get("last_checked_at", 0), url))
    selected = []
    while any(by_state.values()) and len(selected) < limit:
        order = sorted(by_state, key=lambda state: (
            min((pages.get(url, {}).get("last_checked_at", 0) for url in by_state[state]),
                default=float("inf")), state))
        for state in order:
            if by_state[state] and len(selected) < limit:
                selected.append(by_state[state].pop(0))
    return selected


def run_watch(seeds, state_path, snapshot_dir, fetch, *, now, interval=3600, max_pages=100,
              retry_cap=86400, localities=None):
    if interval < 60 or max_pages < 1 or retry_cap < interval:
        raise ValueError("Invalid watch interval, page limit or retry cap")
    snapshot_dir.mkdir(parents=True, exist_ok=True)
    state = json.loads(state_path.read_text()) if state_path.exists() else {
        "version": 1, "pages": {}, "candidates": {}, "events": [], "sequence": 0,
    }
    if state.get("version") != 1:
        raise ValueError("Unsupported watch state version")
    catalog = load_catalog()
    state.setdefault("authority_candidates", {})
    fingerprint_sha = hashlib.sha256(json.dumps(catalog, sort_keys=True).encode()).hexdigest()
    groups = seed_groups(seeds)
    selected = choose_due(groups, state["pages"], now, max_pages)
    statuses, events = Counter(), []
    requests_before = getattr(fetch, "requests", 0)

    def event(kind, url, page_url, digest=""):
        state["sequence"] += 1
        row = {"sequence": state["sequence"], "observed_at": now, "kind": kind,
               "url": url, "page_url": page_url, "snapshot_sha256": digest,
               "live_coverage": False, "served_jurisdiction_verified": False}
        events.append(row)
        state["events"].append(row)

    for url in selected:
        page_event_start = len(events)
        previous = state["pages"].get(url, {})
        page = dict(previous, last_checked_at=now)
        try:
            final, html = fetch(url)
            final = normalize(final)
            if not final or not publishable_url(final):
                raise ValueError("Unsafe or transient final URL")
            digest = hashlib.sha256(html.encode()).hexdigest()
            # Snapshots are the captured UTF-8 HTML representation, not wire bytes.
            path = snapshot_dir / (digest + ".html")
            if not path.exists():
                path.write_bytes(html.encode())
            access = html_access_state(html)
            if access == "blocked_html":
                raise ValueError("Blocked HTML")
            directory_states = set()
            for seed in groups[url]:
                roles = {role.strip() for role in seed.get("page_roles",
                                                          seed.get("page_role", "")).split("|")}
                if roles & {"state_directory_fallback", "state_election_authority"}:
                    directory_states.update(s.strip() for s in seed.get("states",
                                                          seed.get("state", "")).split("|") if s.strip())
            directory_summaries = {}
            for directory_state in sorted(directory_states):
                state_units = [u for u in (localities or []) if u["state"] == directory_state]
                if not state_units:
                    continue
                authority_rows, unresolved = extract_directory(final, html, state_units,
                                                               state=directory_state)
                for row in authority_rows:
                    identity = hashlib.sha256(json.dumps(
                        [row["state"], row["url"], url, row["associated_unit_ids"], row["match_status"]]
                    ).encode()).hexdigest()
                    stored = state["authority_candidates"].get(identity)
                    if stored is None:
                        event("authority_link_candidate", row["url"], url, digest)
                    state["authority_candidates"][identity] = {
                        **row, "first_observed_at": stored["first_observed_at"] if stored else now,
                        "last_observed_at": now,
                    }
                directory_summaries[directory_state] = {
                    "candidate_links": len(authority_rows),
                    "unresolved_unit_ids": [u["jurisdiction_id"] for u in unresolved],
                    "scope": "Directory-label candidates; service and authority association unverified",
                }
            if directory_summaries:
                page["directory_extraction"] = directory_summaries
            candidates = [clean_public_candidate(c) for c in discover(final, html, url, catalog)]
            candidates = [c for c in candidates if c is not None]
            truncated = len(candidates) > 200
            if truncated:
                event("candidate_limit_reached", final, url, digest)
                candidates = candidates[:200]
            current = {c["url"] for c in candidates}
            old = set(previous.get("current_candidate_urls", []))
            if previous.get("snapshot_sha256") != digest:
                event("baseline_captured" if not previous.get("snapshot_sha256") else
                      "page_changed", final, url, digest)
            elif previous.get("fingerprint_sha256") != fingerprint_sha:
                event("fingerprints_reclassified", final, url, digest)
            for candidate in candidates:
                target = candidate["url"]
                record = state["candidates"].get(target)
                if record is None:
                    record = {**candidate, "first_observed_at": now, "parent_pages": [],
                              "seed_associations": [], "next_action": "inspect_candidate",
                              "verification_status": "candidate"}
                    state["candidates"][target] = record
                if url not in record["parent_pages"]:
                    record["parent_pages"].append(url)
                    event("candidate_discovered", target, url, digest)
                elif target not in old:
                    event("candidate_reappeared", target, url, digest)
                record["last_observed_at"] = now
                depth = min(int(seed.get("watch_depth", 0)) + 1 for seed in groups[url])
                record["watch_depth"] = min(record.get("watch_depth", depth), depth)
                for seed in groups[url]:
                    association = {
                        "parent_page": url,
                        "states": seed.get("states", seed.get("state", "")),
                        "associated_unit_ids": seed.get("associated_unit_ids",
                                                        seed.get("jurisdiction_id", "")),
                    }
                    if association not in record["seed_associations"]:
                        record["seed_associations"].append(association)
                record["score"] = max(record["score"], candidate["score"])
                for key in ("signatures", "roles", "provenance"):
                    for value in candidate[key]:
                        if value not in record[key]:
                            record[key].append(value)
                record["source_snapshot_sha256"] = digest
                record["live_coverage"] = False
                record["served_jurisdiction_verified"] = False
            for target in sorted(old - current) if not truncated else []:
                event("link_not_observed_this_capture", target, url, digest)
            page.update(status="application_shell" if access == "application_shell" else "fetched",
                        snapshot_sha256=digest, final_url=final, last_success_at=now,
                        current_candidate_urls=sorted(current | old if truncated else current), failures=0,
                        next_check_at=now + interval, fingerprint_sha256=fingerprint_sha)
            page.pop("failure_class", None)
            page.pop("http_status", None)
        except RequestBudgetExhausted:
            break
        except (httpx.HTTPError, ValueError, KeyError) as exc:
            failures = previous.get("failures", 0) + 1
            status = "artifact_requires_inspection" if isinstance(exc, ArtifactNeedsInspection) else (
                "robots_denied" if isinstance(exc, RobotsDenied) else
                "robots_unresolved" if isinstance(exc, RobotsUnavailable) else "fetch_unresolved")
            page.update(status=status, failure_class=type(exc).__name__, failures=failures,
                        next_check_at=now + min(retry_cap, interval * 2 ** min(failures - 1, 10)))
            if isinstance(exc, httpx.HTTPStatusError):
                page["http_status"] = exc.response.status_code
            event(status, url, url)
        state["pages"][url] = page
        statuses[page["status"]] += 1
        page_events = events[page_event_start:]
        if page_events:
            journal = state_path.parent / "events"
            journal.mkdir(parents=True, exist_ok=True)
            body = json.dumps(page_events, sort_keys=True) + "\n"
            digest = hashlib.sha256(body.encode()).hexdigest()
            event_path = journal / f"{page_events[0]['sequence']:012d}-{digest}.json"
            if not event_path.exists():
                event_path.write_text(body)
        state["events"] = state["events"][-1000:]
        # Events and page checkpoint commit together so retries do not duplicate discovery.
        save(state_path, state)
    summary = {"observed_at": now, "seed_pages": len(groups), "selected_due_pages": len(selected),
               "checked_pages": sum(statuses.values()), "page_statuses": dict(statuses),
               "new_candidates": sum(e["kind"] == "candidate_discovered" for e in events),
               "events": len(events), "retained_candidates": len(state["candidates"]),
               "retained_authority_link_candidates": len(state["authority_candidates"]),
               "http_requests": getattr(fetch, "requests", requests_before) - requests_before,
               "remaining_due_pages": sum(state["pages"].get(url, {}).get("next_check_at", 0) <= now
                                          for url in groups),
               "unvisited_pages": sum(url not in state["pages"] for url in groups),
               "oldest_due_lateness_seconds": max(
                   (max(0, now - state["pages"][url]["next_check_at"]) for url in groups
                    if url in state["pages"]), default=0),
               "live_sources_verified_this_run": 0, "fingerprint_sha256": fingerprint_sha}
    state["last_summary"] = summary
    save(state_path, state)
    return state, events, summary
