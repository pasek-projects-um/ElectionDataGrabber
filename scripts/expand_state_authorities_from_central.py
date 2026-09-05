from __future__ import annotations

import argparse
import csv
import json
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup
from election_data_grabber.state_directory_profiles import structured_candidates, alaska_state_result_candidates

RESULT_RE = re.compile(r"(election\s+results?|unofficial\s+results?|official\s+results?|election\s+night|statement\s+of\s+votes?|canvass|precinct\s+results?)", re.I)
AUTH_RE = re.compile(r"(election|clerk|registrar|board|county|parish|town|city|borough|municipal|ward|district)", re.I)
PLATFORMS = [
    ("enhanced_voting", re.compile(r"enhancedvoting", re.I)),
    ("clarity", re.compile(r"clarityelections|election night reporting", re.I)),
    ("civicplus", re.compile(r"civicplus|civicengage|documentcenter", re.I)),
    ("electionware", re.compile(r"electionware", re.I)),
    ("scytl", re.compile(r"scytl", re.I)),
]


def platform(url: str, text: str) -> str:
    blob = url + " " + text[:150000]
    for name, pattern in PLATFORMS:
        if pattern.search(blob):
            return name
    if ".pdf" in url.lower():
        return "pdf"
    return "unknown_web"


def probe_candidate(client: httpx.Client, state: str, central: str, url: str) -> dict | None:
    try:
        r = client.get(url)
        r.raise_for_status()
    except Exception:
        return None
    soup = BeautifulSoup(r.content, "html.parser")
    text = soup.get_text(" ", strip=True)
    result_links = []
    for a in soup.find_all("a", href=True):
        label = " ".join(a.stripped_strings)
        target = urljoin(str(r.url), str(a["href"]))
        if RESULT_RE.search(label + " " + target):
            result_links.append(target)
    return {
        "state": state,
        "central_authority_url": central,
        "authority_url": str(r.url),
        "authority_host": urlparse(str(r.url)).hostname or "",
        "result_links": " | ".join(dict.fromkeys(result_links[:12])),
        "election_night_candidate": str(bool(re.search(r"election\s+night|unofficial", text, re.I))).lower(),
        "smallest_observed_unit": "precinct" if re.search(r"precinct", text, re.I) else ("ward" if re.search(r"\bward\b", text, re.I) else ""),
        "platform_family": platform(str(r.url), text),
        "status": "reached",
    }


def crawl_state(row: dict[str, str], max_candidates: int) -> list[dict]:
    state = row["state"]
    central = row["central_authority_url"]
    out = []
    with httpx.Client(timeout=10, follow_redirects=True, headers={"User-Agent": "ElectionDataGrabber/0.1 (+academic election research)"}) as client:
        try:
            r = client.get(central)
            r.raise_for_status()
        except Exception as exc:
            return [{"state": state, "central_authority_url": central, "authority_url": "", "authority_host": "", "result_links": "", "election_night_candidate": "", "smallest_observed_unit": "", "platform_family": "", "status": f"central_fetch_failed:{type(exc).__name__}"}]
        soup = BeautifulSoup(r.content, "html.parser")
        candidates = []
        for a in soup.find_all("a", href=True):
            label = " ".join(a.stripped_strings)
            target = urljoin(str(r.url), str(a["href"]))
            if target.startswith("mailto:"):
                continue
            if AUTH_RE.search(label + " " + target):
                candidates.append(target)
        candidates.extend(structured_candidates(state, r.content, str(r.url)))
        if state == "AK":
            candidates.extend(alaska_state_result_candidates(r.content, str(r.url)))
        candidates = list(dict.fromkeys(candidates))[:max_candidates]
        out.append({"state": state, "central_authority_url": str(r.url), "authority_url": str(r.url), "authority_host": urlparse(str(r.url)).hostname or "", "result_links": "", "election_night_candidate": "", "smallest_observed_unit": "", "platform_family": platform(str(r.url), r.text), "status": f"central_reached:{len(candidates)}_candidates"})
        with ThreadPoolExecutor(max_workers=16) as ex:
            futures = [ex.submit(probe_candidate, client, state, str(r.url), u) for u in candidates]
            for fut in as_completed(futures):
                item = fut.result()
                if item:
                    out.append(item)
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--states", nargs="*", default=[])
    ap.add_argument("--max-candidates", type=int, default=160)
    ap.add_argument("--out", type=Path, default=Path("audit/us-state-central-authority-expansion.csv"))
    ap.add_argument("--summary", type=Path, default=Path("audit/us-state-central-authority-summary.json"))
    args = ap.parse_args()

    with Path("registry/us_state_central_authority_sources.csv").open(encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))
    if args.states:
        wanted = set(args.states)
        rows = [r for r in rows if r["state"] in wanted]
    rows.sort(key=lambda r: r["state"])

    all_rows = []
    # Keep state-level concurrency modest so central sites are not hammered.
    with ThreadPoolExecutor(max_workers=min(6, max(1, len(rows)))) as ex:
        futures = {ex.submit(crawl_state, row, args.max_candidates): row["state"] for row in rows}
        for i, fut in enumerate(as_completed(futures), 1):
            state = futures[fut]
            got = fut.result()
            all_rows.extend(got)
            print(f"[{i}/{len(futures)}] {state}: {len(got)} rows")

    args.out.parent.mkdir(parents=True, exist_ok=True)
    fields = ["state", "central_authority_url", "authority_url", "authority_host", "result_links", "election_night_candidate", "smallest_observed_unit", "platform_family", "status"]
    with args.out.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(all_rows)

    by_state = {}
    for state in sorted({r["state"] for r in all_rows}):
        srows = [r for r in all_rows if r["state"] == state]
        reached = sum(r["status"] == "reached" for r in srows)
        with_results = sum(bool(r["result_links"]) for r in srows)
        if reached >= 3:
            exposure = "direct"
        elif reached >= 1:
            exposure = "indirect"
        elif any(r["status"].startswith("central_reached") for r in srows):
            exposure = "state_only"
        else:
            exposure = "unresolved"
        by_state[state] = {
            "rows": len(srows),
            "reached": reached,
            "with_result_links": with_results,
            "election_night_candidates": sum(r["election_night_candidate"] == "true" for r in srows),
            "local_site_exposure": exposure,
        }
    summary = {"states": len(rows), "rows": len(all_rows), "by_state": by_state}
    args.summary.write_text(json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")
    print("SUMMARY", json.dumps(summary, sort_keys=True))


if __name__ == "__main__":
    main()
