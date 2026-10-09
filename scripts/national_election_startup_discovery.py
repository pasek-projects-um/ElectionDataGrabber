from __future__ import annotations

"""Nationwide, bounded startup discovery around known election authority pages.

Seeds are leads from existing registries, not assertions that results are live.
All URLs remain tied to their original jurisdiction; unresponsive sites do not
erase historical evidence. The crawl never leaves a page's own hostname except
for explicitly linked election-result vendor hosts.
"""

import csv
import json
import re
from collections import Counter, deque
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urljoin, urlsplit, urldefrag

import httpx
from bs4 import BeautifulSoup

RESULT = re.compile(r"results?|election.night|unofficial|precinct|canvass|tabulation|statement.of.votes", re.I)
ELECTION = re.compile(
    r"elections?|voting|voter.?information|ballot|clerk|registrar|"
    r"board.of.elections|election.commission|election.office|county.auditor|"
    r"election.division|supervisor.of.elections|general.election|"
    r"past.elections?|previous.elections?|archives?|election.history|"
    r"election.database|election.portal|election.calendar", re.I
)
ELECTION_PICKER = re.compile(
    r"2026|november|general.election|select.election|choose.election|"
    r"election.details?|election.history|past.elections?", re.I
)
VENDOR = ("enhancedvoting.com", "clarityelections.com", "electionreporting.com")
FIELDS = ("jurisdiction_id", "state", "jurisdiction_level", "seed_url", "url",
          "depth", "category", "status", "platform_family", "error_class")


@dataclass(frozen=True)
class Seed:
    jurisdiction_id: str
    state: str
    jurisdiction_level: str
    url: str


def safe_url(value: str, base: str = "") -> str | None:
    value = value.strip()
    if not value or value.lower().startswith(("javascript:", "mailto:", "data:")):
        return None
    url = urldefrag(urljoin(base, value))[0]
    parsed = urlsplit(url)
    if parsed.scheme.lower() not in ("https", "http") or not parsed.hostname:
        return None
    if parsed.username or parsed.password:
        return None
    return url


def load_seeds(root: str | Path = "registry") -> list[Seed]:
    root = Path(root)
    seeds: dict[tuple[str, str], Seed] = {}

    def add(jurisdiction, state, level, url):
        url = safe_url(url)
        if not jurisdiction or not url:
            return
        key = (jurisdiction, url)
        seeds[key] = Seed(jurisdiction, state, level, url)

    path = root / "us_primary_election_localities.csv"
    with path.open(encoding="utf-8-sig", newline="") as stream:
        for row in csv.DictReader(stream):
            for field in ("election_night_evidence_url", "final_evidence_url"):
                add(row["jurisdiction_id"], row["state"], row["jurisdiction_level"], row.get(field, ""))
    path = root / "us_state_central_authority_sources.csv"
    with path.open(encoding="utf-8-sig", newline="") as stream:
        for row in csv.DictReader(stream):
            state = row["state"].upper()
            add(f"us:{state.lower()}", state, "state", row.get("central_authority_url", ""))
    path = root / "us_local_reporting_sources.csv"
    with path.open(encoding="utf-8-sig", newline="") as stream:
        for row in csv.DictReader(stream):
            state = row.get("state", "").upper()
            identity = f"us:{state.lower()}:{row.get('locality_type','unknown')}:{row.get('locality_name','unknown')}".lower()
            for field in ("authority_url", "results_url"):
                for url in row.get(field, "").split("|"):
                    add(identity, state, row.get("locality_type", ""), url)
    path = root / "sources.csv"
    if path.exists():
        with path.open(encoding="utf-8-sig", newline="") as stream:
            for row in csv.DictReader(stream):
                if row.get("official", "").lower() != "true":
                    continue
                state = row.get("state", "").upper()
                add(f"us:{state.lower()}:source:{row.get('source_id', '')}", state,
                    "source", row.get("url", ""))
    return sorted(seeds.values(), key=lambda item: (item.state, item.jurisdiction_id, item.url))


def platform(url: str) -> str:
    host = (urlsplit(url).hostname or "").lower()
    if "enhancedvoting" in host:
        return "enhanced_voting"
    if "clarityelections" in host:
        return "clarity"
    if "electionreporting" in host:
        return "election_reporting"
    return "unknown_web"


def allowed_link(seed_url: str, candidate: str) -> bool:
    seed_host = (urlsplit(seed_url).hostname or "").lower()
    host = (urlsplit(candidate).hostname or "").lower()
    return host == seed_host or host.endswith("." + seed_host) or any(
        host == vendor or host.endswith("." + vendor) for vendor in VENDOR
    )


def crawl_seed(seed: Seed, client: httpx.Client, *, max_pages: int = 8, max_depth: int = 2) -> list[dict]:
    if max_pages < 1 or max_depth < 0:
        raise ValueError("max_pages must be positive and max_depth must not be negative")
    queue = deque([(seed.url, 0, "election_site")])
    visited: set[str] = set()
    rows = []
    while queue and len(visited) < max_pages:
        url, depth, category = queue.popleft()
        if url in visited:
            continue
        visited.add(url)
        status = "reachable"
        error = ""
        html = ""
        try:
            response = client.get(url)
            response.raise_for_status()
            if "html" in response.headers.get("content-type", "").lower():
                html = response.text[:500000]
        except httpx.HTTPError as exc:
            status = "fetch_failed"
            error = type(exc).__name__
        rows.append({"jurisdiction_id": seed.jurisdiction_id, "state": seed.state,
                     "jurisdiction_level": seed.jurisdiction_level, "seed_url": seed.url,
                     "url": url, "depth": depth, "category": category, "status": status,
                     "platform_family": platform(url), "error_class": error})
        if status != "reachable" or depth >= max_depth or not html:
            continue
        soup = BeautifulSoup(html, "html.parser")
        candidates = []
        for link in soup.select("a[href]"):
            raw = str(link.get("href", ""))
            link_url = safe_url(raw, str(response.url))
            if not link_url or not allowed_link(seed.url, link_url):
                continue
            label = " ".join(link.stripped_strings)
            phrase = label + " " + link_url
            result = bool(RESULT.search(phrase))
            election = bool(ELECTION.search(phrase) or ELECTION_PICKER.search(phrase))
            if result or election:
                candidates.append((0 if result else 1, link_url, "result_lead" if result else "election_site"))
        for _, link_url, kind in sorted(candidates):
            if link_url not in visited and all(existing[0] != link_url for existing in queue):
                queue.append((link_url, depth + 1, kind))
    return rows


def run(seeds, *, max_seeds=100, max_pages=8, max_depth=2, client=None):
    selected = list(seeds)[:max_seeds]
    if client is not None:
        return [row for seed in selected for row in crawl_seed(seed, client, max_pages=max_pages, max_depth=max_depth)]
    with httpx.Client(timeout=8, follow_redirects=True,
                      headers={"User-Agent": "ElectionDataGrabber/0.1 (+research; bounded election discovery)"}) as session:
        return [row for seed in selected for row in crawl_seed(seed, session, max_pages=max_pages, max_depth=max_depth)]


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--max-seeds", type=int, default=100)
    parser.add_argument("--max-pages", type=int, default=8)
    parser.add_argument("--max-depth", type=int, default=2)
    parser.add_argument("--output", default="audit")
    args = parser.parse_args()
    if args.max_seeds < 1:
        parser.error("--max-seeds must be positive")
    rows = run(load_seeds(), max_seeds=args.max_seeds, max_pages=args.max_pages, max_depth=args.max_depth)
    target = Path(args.output)
    target.mkdir(parents=True, exist_ok=True)
    with (target / "national-election-startup-discovery.csv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    summary = {"seed_limit": args.max_seeds, "jurisdictions": len(set(row["jurisdiction_id"] for row in rows)),
               "pages": len(rows), "statuses": dict(Counter(row["status"] for row in rows)),
               "categories": dict(Counter(row["category"] for row in rows)),
               "platform_families": dict(Counter(row["platform_family"] for row in rows))}
    (target / "national-election-startup-summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True))
    print(json.dumps(summary, sort_keys=True))


if __name__ == "__main__":
    main()
