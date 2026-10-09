"""Targeted Wayback CDX discovery for uncertain election-jurisdiction starting URLs.

Only searches explicit election windows: 2024 general, supplied 2025 election
dates, and supplied 2026 primary dates. No arbitrary year-wide crawling.
"""
from __future__ import annotations

import argparse
import csv
import json
import re
from datetime import date, timedelta
from pathlib import Path
from urllib.parse import urlsplit

import httpx

CDX = "https://web.archive.org/cdx/search/cdx"
HINT = re.compile(r"(election|results?|vot(e|ing)|clerk|primary|canvass|enr|reporting)", re.I)
FIELDS = ("jurisdiction_id", "seed_url", "election_type", "election_date",
          "snapshot_timestamp", "archived_url", "original_url", "candidate_role",
          "evidence_status")


def windows(election_type: str, election_day: str):
    day = date.fromisoformat(election_day)
    if (election_type == "2024_general" and day != date(2024, 11, 5)
            or election_type == "2025_election" and day.year != 2025
            or election_type == "2026_primary" and day.year != 2026):
        raise ValueError("Election type and date do not match allowed windows")
    return ((day - timedelta(days=3)).strftime("%Y%m%d"),
            (day + timedelta(days=10)).strftime("%Y%m%d"))


def archive_candidates(jurisdiction_id, seed_url, election_type, election_day, client,
                       max_snapshots=10):
    start, end = windows(election_type, election_day)
    parsed = urlsplit(seed_url)
    if parsed.scheme not in ("http", "https") or not parsed.hostname:
        return []
    params = {"url": seed_url, "output": "json", "filter": "statuscode:200",
              "filter": "mimetype:text/html", "collapse": "timestamp:4",
              "from": start, "to": end, "fl": "timestamp,original,statuscode",
              "limit": str(max_snapshots)}
    response = client.get(CDX, params=params)
    response.raise_for_status()
    payload = response.json()
    rows = []
    if not isinstance(payload, list):
        return rows
    for item in payload[1:max_snapshots + 1]:
        if not isinstance(item, list) or len(item) < 2:
            continue
        timestamp, original = item[:2]
        if not re.fullmatch(r"\d{14}", str(timestamp)):
            continue
        if not (start <= str(timestamp)[:8] <= end):
            continue
        archived = f"https://web.archive.org/web/{timestamp}/{original}"
        try:
            page = client.get(archived)
            page.raise_for_status()
        except httpx.HTTPError:
            continue
        # Extract only archived links; never treat them as current verified URLs.
        for raw in re.findall(r"""href\s*=\s*["']([^"']+)["']""", page.text, re.I):
            if not HINT.search(raw):
                continue
            if raw.startswith(("javascript:", "mailto:", "#")):
                continue
            from urllib.parse import urljoin
            candidate = urljoin(original, raw)
            if candidate.startswith("https://web.archive.org/web/"):
                match = re.match(r"https://web\.archive\.org/web/\d+(?:[a-z_]+)?/(https?://.+)", candidate)
                if match:
                    candidate = match.group(1)
            p = urlsplit(candidate)
            if p.scheme not in ("http", "https") or not p.hostname:
                continue
            rows.append(dict(zip(FIELDS, (
                jurisdiction_id, seed_url, election_type, election_day,
                timestamp, archived, candidate, "historical_election_link",
                "archived_only_unverified_current"))))
    return list({(row["snapshot_timestamp"], row["original_url"]): row
                 for row in rows}.values())


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--targets", required=True,
                        help="CSV: jurisdiction_id,seed_url,election_type,election_date")
    parser.add_argument("--output", default="audit/wayback-starting-point-leads.csv")
    args = parser.parse_args()
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    rows = []
    with httpx.Client(timeout=12, follow_redirects=True,
                      headers={"User-Agent": "ElectionDataGrabber/0.1 election source research"}) as client:
        with open(args.targets, newline="", encoding="utf-8-sig") as stream:
            for target in csv.DictReader(stream):
                rows.extend(archive_candidates(target["jurisdiction_id"], target["seed_url"],
                                               target["election_type"], target["election_date"], client))
    with output.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    print(json.dumps({"historical_leads": len(rows), "output": str(output)}))


if __name__ == "__main__":
    main()
