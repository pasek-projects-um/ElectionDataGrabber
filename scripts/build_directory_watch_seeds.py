"""Queue uniquely labeled directory URLs for inspection, never source verification."""

import argparse
import csv
from pathlib import Path
from urllib.parse import urlsplit

from election_data_grabber.discovery_publication import publishable_url
from election_data_grabber.discovery_watch import ARTIFACT_PATH
from election_data_grabber.national_discovery import normalize

FIELDS = ["url", "states", "associated_unit_ids", "page_roles", "observed_from",
          "snapshot_sha256", "match_basis", "served_jurisdiction_verified", "live_coverage"]
ROLES = {"authority_website_lead", "external_website_lead", "result_page_lead"}


def build(rows):
    output = {}
    for row in rows:
        url = normalize(row.get("url", ""))
        units = [u.strip() for u in row.get("associated_unit_ids", "").split("|") if u.strip()]
        digest = row.get("snapshot_sha256", "")
        if (row.get("match_status") != "unit_label_candidate" or len(units) != 1
                or row.get("link_role") not in ROLES or not row.get("state")
                or not row.get("observed_from") or len(digest) != 64
                or any(c not in "0123456789abcdef" for c in digest)
                or not url or not publishable_url(url)
                or ARTIFACT_PATH.search(urlsplit(url).path)):
            continue
        seed = dict(zip(FIELDS, [url, row["state"], units[0], "directory_inspection_lead",
                                row["observed_from"], digest, row.get("match_basis", ""),
                                "false", "false"]))
        key = (url, row["state"], units[0], row["observed_from"], digest)
        output[key] = seed
    return [output[key] for key in sorted(output)]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, action="append", default=None)
    parser.add_argument("--output", type=Path, default=Path("watch-data/directory-seeds.csv"))
    args = parser.parse_args()
    rows = []
    for path in args.input or [Path("audit/authority-directory-national/directory-link-candidates.csv")]:
        with path.open(newline="", encoding="utf-8-sig") as stream:
            rows.extend(csv.DictReader(stream))
    seeds = build(rows)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=FIELDS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(seeds)
    print(f"{len(seeds)} inspection associations; {len({s['url'] for s in seeds})} URLs")


if __name__ == "__main__":
    main()
