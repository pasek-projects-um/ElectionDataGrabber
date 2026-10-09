"""Evidence-first discovery: fingerprints never verify sources or live coverage."""

from __future__ import annotations

import hashlib
import ipaddress
import json
import re
import time
from collections import Counter, defaultdict
from datetime import UTC, datetime
from html import unescape
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urljoin, urlsplit, urlunsplit

import httpx
from bs4 import BeautifulSoup

CATALOG = Path(__file__).resolve().parents[2] / "registry/dashboard_fingerprints.json"
RESULT = re.compile(
    r"election[\s/_-]*results?|unofficial[\s/_-]*results?|statement\s+of\s+votes?|canvass",
    re.IGNORECASE,
)


def normalize(url, base=""):
    try:
        p = urlsplit(urljoin(base, unescape(url.strip())))
        if p.scheme not in ("http", "https") or not p.hostname or p.username:
            return ""
        host = p.hostname.lower()
        if host == "localhost" or host.endswith((".local", ".localhost")):
            return ""
        try:
            if not ipaddress.ip_address(host).is_global:
                return ""
        except ValueError:
            pass
        if p.port and p.port not in (80, 443):
            return ""
        if ":" in host:
            host = f"[{host}]"
        path = re.sub(
            r"%([0-9a-fA-F]{2})",
            lambda m: (
                chr(int(m[1], 16))
                if chr(int(m[1], 16))
                in "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-._~"
                else "%" + m[1].upper()
            ),
            p.path or "/",
        )
        query = urlencode(
            sorted(
                (k, v)
                for k, v in parse_qsl(p.query, keep_blank_values=True)
                if not k.lower().startswith("utm_")
            )
        )
        return urlunsplit((p.scheme, host, path, query, ""))
    except ValueError:
        return ""


def load_catalog(path=CATALOG):
    catalog = json.loads(path.read_text())
    ids = set()
    for r in catalog["rules"]:
        if r["id"] in ids or r["role"] not in (
            "result_platform",
            "authority_discovery",
            "report_family",
        ):
            raise ValueError("Invalid fingerprint")
        if not r["evidence"] or not 0 <= r["weight"] <= 100:
            raise ValueError("Missing evidence/invalid weight")
        re.compile(r["pattern"])
        ids.add(r["id"])
    return catalog


def matches(url, text="", catalog=None, html=""):
    p = urlsplit(url)
    fields = {"host": p.hostname or "", "path": p.path, "url": url, "text": text, "html": html}
    return [
        r
        for r in (catalog or load_catalog())["rules"]
        if re.search(r["pattern"], fields[r["field"]], re.IGNORECASE)
    ]


def discover(page_url, html, requested_url="", catalog=None):
    catalog = catalog or load_catalog()
    soup = BeautifulSoup(html, "html.parser")
    base_tag = soup.find("base", href=True)
    resolution_base = normalize(base_tag["href"], page_url) if base_tag else page_url
    resolution_base = resolution_base or page_url
    targets = [(page_url, "response", soup.get_text(" ", strip=True))]
    if requested_url and normalize(requested_url) != normalize(page_url):
        targets.append((page_url, "redirect", requested_url))
    for tag in soup.find_all(["a", "iframe", "script", "link", "meta"]):
        if tag.name == "a":
            targets.append((tag.get("href", ""), "link", tag.get_text(" ", strip=True)))
        elif tag.name in ("iframe", "script") and tag.get("src"):
            targets.append((tag["src"], tag.name, ""))
        elif tag.name == "link" and "canonical" in tag.get("rel", []):
            targets.append((tag.get("href", ""), "canonical", ""))
        elif tag.name == "meta" and tag.get("http-equiv", "").lower() == "refresh":
            m = re.search(r'url\s*=\s*[\'"]?([^\'"]+)', tag.get("content", ""), re.IGNORECASE)
            if m:
                targets.append((m[1], "meta_redirect", ""))
    for script in soup.find_all("script"):
        body = script.string or ""
        for m in re.finditer(
            r"""(?:location(?:\.href)?\s*=|location\.replace\(|fetch\()\s*["']([^"']+)["']""", body
        ):
            targets.append((m[1], "embedded", ""))
        for m in re.finditer(r"""["'](https?://[^"'<>\s]+)["']""", body):
            targets.append((m[1], "embedded", ""))
    rows = {}
    for raw, kind, label in targets:
        url = normalize(raw, resolution_base) if raw else ""
        if not url:
            continue
        signatures = matches(url, label, catalog, html if kind == "response" else "")
        keyword = bool(RESULT.search(url + " " + label))
        if not signatures and not keyword:
            continue
        row = rows.setdefault(
            url,
            {
                "url": url,
                "score": 0,
                "signatures": [],
                "roles": [],
                "provenance": [],
                "verification_status": "candidate",
                "live_coverage": False,
            },
        )
        row["score"] = max(
            row["score"],
            min(100, max((s["weight"] for s in signatures), default=0) + (20 if keyword else 0)),
        )
        for s in signatures:
            if s["id"] not in row["signatures"]:
                row["signatures"].append(s["id"])
            if s["role"] not in row["roles"]:
                row["roles"].append(s["role"])
        evidence = {
            "page_url": page_url,
            "resolution_base": resolution_base,
            "kind": kind,
            "raw_target": raw,
            "label": label[:500],
            "keyword_match": keyword,
        }
        if evidence not in row["provenance"]:
            row["provenance"].append(evidence)
    return sorted(rows.values(), key=lambda r: (-r["score"], r["url"]))


def publisher_key(url):
    p = urlsplit(normalize(url))
    if (p.hostname or "").endswith(".clarityelections.com"):
        m = re.match(r"(/[^/]+/[^/]+/\d+/)", p.path)
        if m:
            return urlunsplit((p.scheme, p.netloc, m[1], "", ""))
    m = re.match(r"(/results/public/[^/]+/elections/[^/]+)", p.path)
    if (
        p.hostname
        in (
            "app.enhancedvoting.com",
            "results.sos.ga.gov",
            "electionresults.utah.gov",
            "enr.elections.virginia.gov",
        )
        and m
    ):
        return urlunsplit((p.scheme, p.netloc, m[1], p.query, ""))
    return normalize(url)


def assess(html, name, election):
    text = BeautifulSoup(html, "html.parser").get_text(" ", strip=True)
    evidence = {
        "results_content": bool(RESULT.search(text)),
        "jurisdiction_context": bool(
            len(name.strip()) > 2
            and re.search(r"(?<!\w)" + re.escape(name) + r"(?!\w)", text, re.IGNORECASE)
        ),
        "election_context": bool(
            election
            and re.search(r"(?<!\w)" + re.escape(election) + r"(?!\w)", text, re.IGNORECASE)
        ),
    }
    return {
        "verification_status": "context_supported"
        if all(evidence.values())
        else "fetched_unverified",
        "verification_evidence": evidence,
        "live_coverage": False,
    }


def html_access_state(html):
    soup = BeautifulSoup(html, "html.parser")
    title = soup.title.get_text(" ", strip=True).casefold() if soup.title else ""
    text = soup.get_text(" ", strip=True)
    if title in ("just a moment...", "request rejected", "access denied") or text.startswith(
        "Request Rejected The requested URL was rejected"
    ):
        return "blocked_html"
    if soup.find("app-root") or "{{" in text:
        return "application_shell"
    return "html_content"


class RequestBudgetExhausted(Exception):
    pass


class ArtifactNeedsInspection(ValueError):
    pass


class Fetcher:
    def __init__(self, delay=1.0, max_bytes=1_000_000, max_requests=1000, snapshot_dir=None):
        self.delay, self.max_bytes, self.last = delay, max_bytes, {}
        self.remaining = max_requests
        self.requests = 0
        self.snapshot_dir = Path(snapshot_dir) if snapshot_dir else None
        self.client = httpx.Client(
            timeout=15,
            follow_redirects=False,
            headers={"User-Agent": "ElectionDataGrabber/0.1 academic discovery"},
        )

    def __call__(self, url):
        for _ in range(6):
            url = normalize(url)
            if not url:
                raise ValueError("Unsafe redirect")
            if self.remaining <= 0:
                raise RequestBudgetExhausted()
            self.remaining -= 1
            self.requests += 1
            host = urlsplit(url).hostname
            time.sleep(max(0, self.delay - (time.monotonic() - self.last.get(host, 0))))
            self.last[host] = time.monotonic()
            with self.client.stream("GET", url) as r:
                if r.status_code in (301, 302, 303, 307, 308):
                    url = urljoin(url, r.headers["location"])
                    continue
                r.raise_for_status()
                if "html" not in r.headers.get("content-type", "").lower():
                    raise ArtifactNeedsInspection("Artifact requires separate inspection")
                data = bytearray()
                for chunk in r.iter_bytes():
                    data.extend(chunk)
                    if len(data) > self.max_bytes:
                        raise ValueError("Response exceeds byte limit")
                html = data.decode(r.encoding or "utf-8", errors="replace")
                if self.snapshot_dir:
                    self.snapshot_dir.mkdir(parents=True, exist_ok=True)
                    digest = hashlib.sha256(html.encode()).hexdigest()
                    (self.snapshot_dir / (digest + ".html")).write_text(html)
                return url, html
        raise ValueError("Redirect limit")

    def close(self):
        self.client.close()


def run_batch(
    seeds,
    checkpoint,
    fetch,
    *,
    max_publishers=150,
    max_requests=300,
    max_depth=1,
    election="",
    retry_failed=False,
):
    catalog = load_catalog()
    identity = hashlib.sha256(
        json.dumps([seeds, catalog, max_depth, election], sort_keys=True).encode()
    ).hexdigest()
    state = (
        json.loads(checkpoint.read_text())
        if checkpoint.exists()
        else {
            "identity": identity,
            "selection_policy": "state_round_robin_v1",
            "catalog_version": catalog["version"],
            "pages": {},
            "publishers": {},
            "associations": [],
        }
    )
    if state["identity"] != identity:
        raise ValueError("Checkpoint input/catalog/config mismatch")
    groups = {}
    for seed in seeds:
        url = normalize(seed["url"])
        if url:
            groups.setdefault(url, []).append(seed)
    by_state = defaultdict(list)
    for url, group in groups.items():
        by_state[min(s.get("state", "") for s in group)].append(url)
    for state_urls in by_state.values():
        state_urls.sort(
            key=lambda u: (
                all(s.get("page_role") == "state_directory_fallback" for s in groups[u]),
                u,
            )
        )
    selected = []
    while len(selected) < max_publishers and any(by_state.values()):
        for state_name in sorted(by_state):
            if by_state[state_name] and len(selected) < max_publishers:
                selected.append(by_state[state_name].pop(0))
    queue = [(url, 0, url) for url in selected]
    requests, seen = 0, set()
    association_keys = {
        (a["jurisdiction_id"], a["seed_url"], a["candidate_url"], a["authority_id"])
        for a in state["associations"]
    }
    while queue:
        url, depth, origin = queue.pop(0)
        if (url, origin) in seen:
            continue
        seen.add((url, origin))
        page = state["pages"].get(url)
        if page is None or (retry_failed and page["status"] == "fetch_failed"):
            if requests >= max_requests:
                continue
            requests += 1
            try:
                final, html = fetch(url)
                final = normalize(final)
                if not final:
                    raise ValueError("Invalid final URL")
                page = {
                    "status": "fetched",
                    "observed_at": datetime.now(UTC).isoformat(),
                    "final_url": final,
                    "sha256": hashlib.sha256(html.encode()).hexdigest(),
                    "candidates": discover(final, html, url, catalog),
                    "text": BeautifulSoup(html, "html.parser").get_text(" ", strip=True),
                    "access_state": html_access_state(html),
                }
            except RequestBudgetExhausted:
                break
            except ArtifactNeedsInspection as exc:
                page = {"status": "artifact_needs_inspection", "error": str(exc), "candidates": []}
            except (httpx.HTTPError, ValueError, KeyError) as exc:
                page = {"status": "fetch_failed", "error": type(exc).__name__, "candidates": []}
                if isinstance(exc, httpx.HTTPStatusError):
                    page["http_status"] = exc.response.status_code
            if page.get("access_state") == "blocked_html":
                page["status"] = "blocked_html"
                page["candidates"] = []
            state["pages"][url] = page
        for candidate in page["candidates"][:50]:
            key = publisher_key(candidate["url"])
            pub = state["publishers"].setdefault(key, {"publisher_key": key, "candidates": {}})
            existing = pub["candidates"].get(candidate["url"])
            if existing:
                for evidence in candidate["provenance"]:
                    if evidence not in existing["provenance"]:
                        existing["provenance"].append(evidence)
                existing["score"] = max(existing["score"], candidate["score"])
            else:
                pub["candidates"][candidate["url"]] = json.loads(json.dumps(candidate))
            if (
                depth < max_depth
                and candidate["score"] >= 20
                and any(p["kind"] != "script" for p in candidate["provenance"])
                and not re.search(
                    r"\.(pdf|csv|xlsx?|xml|json|zip|js|css)$",
                    urlsplit(candidate["url"]).path,
                    re.IGNORECASE,
                )
            ):
                queue.append((candidate["url"], depth + 1, origin))
            for seed in groups[origin]:
                association = {
                    "authority_id": seed.get("authority_id", ""),
                    "jurisdiction_id": seed["jurisdiction_id"],
                    "publisher_key": key,
                    "seed_url": origin,
                    "source_scope": seed.get("page_role", "unknown"),
                    "candidate_url": candidate["url"],
                    "served_jurisdiction_verified": False,
                    "live_coverage": False,
                }
                association_key = tuple(
                    association[k]
                    for k in ("jurisdiction_id", "seed_url", "candidate_url", "authority_id")
                )
                if association_key not in association_keys:
                    state["associations"].append(association)
                    association_keys.add(association_key)
        save(checkpoint, state)
    seed_lookup = {(url, s["jurisdiction_id"]): s for url, group in groups.items() for s in group}
    for a in state["associations"]:
        page = state["pages"].get(a["candidate_url"], {})
        seed = seed_lookup[(a["seed_url"], a["jurisdiction_id"])]
        if page.get("status") == "fetched":
            a.update(assess(page["text"], seed.get("jurisdiction_name", ""), election))
        else:
            a["verification_status"] = page.get("status", "candidate")
    state["summary"] = {
        "selected_seed_publishers": len(selected),
        "selected_states": sorted({s.get("state", "") for u in selected for s in groups[u]}),
        "page_statuses": dict(Counter(p["status"] for p in state["pages"].values())),
        "candidate_limit_per_page": 50,
        "requests_this_run": requests,
        "pages": len(state["pages"]),
        "catalog_sha256": hashlib.sha256(json.dumps(catalog, sort_keys=True).encode()).hexdigest(),
        "candidate_publishers": len(state["publishers"]),
        "verified_live_sources": 0,
        "http_requests_this_run": getattr(fetch, "requests", requests),
        "verification_states": dict(
            Counter(a["verification_status"] for a in state["associations"])
        ),
        "signature_hits": dict(
            Counter(
                s
                for p in state["publishers"].values()
                for c in p["candidates"].values()
                for s in c["signatures"]
            )
        ),
    }
    save(checkpoint, state)
    return state


def save(path, state):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(state, indent=2, sort_keys=True) + "\n")
    tmp.replace(path)
