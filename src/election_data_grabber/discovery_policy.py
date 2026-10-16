"""Pause search effort on evidence of diminishing returns, never certify coverage."""

from collections import defaultdict
from datetime import datetime
from urllib.parse import urlsplit

from election_data_grabber.discovery_publication import publishable_url
from election_data_grabber.discovery_watch import ARTIFACT_PATH
from election_data_grabber.national_discovery import normalize

QUIET_OUTCOME = "completed_no_new_urls"


def timestamp(value):
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return parsed.timestamp() if parsed.tzinfo else 0
    except (ValueError, TypeError, AttributeError):
        return 0


def discovery_frontier(localities, leads, attempts, *, now, watch_state=None,
                       quiet_limit=3, monitor_interval=86400):
    """Only explicit completed no-gain rounds count; new distinct evidence reopens."""
    evidence = defaultdict(dict)
    units = {u["jurisdiction_id"]: u for u in localities}
    for lead in leads:
        url = normalize(lead.get("url", ""))
        observed = timestamp(lead.get("observed_at"))
        unit = units.get(lead.get("jurisdiction_id"))
        if (unit and lead.get("state") == unit["state"] and url and observed
                and lead.get("evidence_status") == "observed_link_candidate"
                and publishable_url(url)):
            by_url = evidence[lead.get("jurisdiction_id", "")]
            by_url[url] = min(by_url.get(url, observed), observed)
    for candidate in (watch_state or {}).get("candidates", {}).values():
        observed = candidate.get("first_observed_at", 0)
        url = candidate.get("url", "")
        for association in candidate.get("seed_associations", []):
            for unit_id in association.get("associated_unit_ids", "").split("|"):
                by_url = evidence[unit_id.strip()]
                if url and observed:
                    by_url[url] = min(by_url.get(url, observed), observed)
    rounds = defaultdict(lambda: defaultdict(set))
    for attempt in attempts:
        when = timestamp(attempt.get("attempted_at"))
        if when:
            rounds[attempt.get("jurisdiction_id", "")][when].add(attempt.get("outcome", ""))
    rows = []
    for unit in localities:
        unit_id = unit["jurisdiction_id"]
        growth = max(evidence[unit_id].values(), default=0)
        quiet = 0
        last_attempt = 0
        for when, outcomes in sorted(rounds[unit_id].items()):
            last_attempt = max(last_attempt, when)
            if when <= growth:
                continue
            if "observed_link_candidate" in outcomes:
                quiet = 0
            elif outcomes == {QUIET_OUTCOME}:
                quiet += 1
            # Blocks, partial rounds and timeouts neither prove exhaustion nor increment it.
        paused = quiet >= quiet_limit
        # Search rounds are separated by six hours; parked jurisdictions get daily review.
        next_search = last_attempt + (monitor_interval if paused else 21600) if last_attempt else 0
        if growth > last_attempt:
            next_search = 0
        rows.append({
            "jurisdiction_id": unit_id, "state": unit["state"],
            "unit_name": unit.get("canonical_name", ""),
            "discovery_status": "exhausted_for_now" if paused else "active",
            "observed_candidate_urls": len(evidence[unit_id]),
            "completed_quiet_rounds": quiet, "last_attempt_at": last_attempt,
            "last_new_evidence_at": growth, "next_search_at": next_search,
            "search_due": now >= next_search, "coverage_complete": "false",
        })
    return rows


def search_queue(frontier, limit=20):
    """Rotate states by latest attempt, then select their least recently searched units."""
    by_state = defaultdict(list)
    latest = defaultdict(float)
    for row in frontier:
        latest[row["state"]] = max(latest[row["state"]], row["last_attempt_at"])
        if row["search_due"]:
            by_state[row["state"]].append(row)
    for rows in by_state.values():
        rows.sort(key=lambda row: (row["last_attempt_at"], row["jurisdiction_id"]))
    selected = []
    while any(by_state.values()) and len(selected) < limit:
        for state in sorted(by_state, key=lambda state: (latest[state], state)):
            if by_state[state] and len(selected) < limit:
                selected.append(by_state[state].pop(0))
    return selected


def monitoring_seeds(seeds, state, frontier, *, now, monitor_interval=86400):
    """Park expansion for quiet units, retain roots/top three HTML targets for review."""
    paused = {r["jurisdiction_id"] for r in frontier
              if r["discovery_status"] == "exhausted_for_now"}
    best = defaultdict(list)
    for url, candidate in state.get("candidates", {}).items():
        if ARTIFACT_PATH.search(urlsplit(url).path):
            continue
        for association in candidate.get("seed_associations", []):
            for unit_id in association.get("associated_unit_ids", "").split("|"):
                best[unit_id.strip()].append((candidate.get("score", 0), url))
    keep = {unit_id: {url for _, url in sorted(urls, reverse=True)[:3]}
            for unit_id, urls in best.items()}
    output = []
    for seed in seeds:
        units = {u.strip() for u in seed.get("associated_unit_ids", "").split("|") if u.strip()}
        if not units or not units.issubset(paused):
            output.append(seed)
            continue
        url = seed["url"]
        if seed.get("watch_depth", 0) and not any(url in keep.get(u, set()) for u in units):
            continue
        page = state.get("pages", {}).get(url, {})
        if not page.get("last_success_at") or now >= page["last_success_at"] + monitor_interval:
            output.append(seed)
    return output
