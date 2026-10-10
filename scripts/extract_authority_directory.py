"""Build a review queue from a saved official directory capture; no network calls."""

import argparse
import csv
import json
from collections import Counter
from pathlib import Path

from election_data_grabber.authority_directory import FIELDS, extract_directory


def write(path, rows, fields):
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--html", type=Path, required=True)
    parser.add_argument("--page-url", required=True)
    parser.add_argument("--state", required=True)
    parser.add_argument("--registry", type=Path, default=Path("registry"))
    parser.add_argument("--output", type=Path, default=Path("audit/authority-directory"))
    args = parser.parse_args()
    with (args.registry / "us_primary_election_localities.csv").open(
            newline="", encoding="utf-8-sig") as stream:
        units = list(csv.DictReader(stream))
    rows, unresolved = extract_directory(args.page_url, args.html.read_bytes().decode("utf-8"),
                                         units, state=args.state.upper())
    args.output.mkdir(parents=True, exist_ok=True)
    write(args.output / "authority-link-candidates.csv", rows, FIELDS)
    write(args.output / "unresolved-units.csv", unresolved,
          ("jurisdiction_id", "state", "jurisdiction_name", "next_action", "reason"))
    summary = {"state": args.state.upper(), "candidate_links": len(rows),
               "match_statuses": dict(Counter(r["match_status"] for r in rows)),
               "units_without_unambiguous_website_label": len(unresolved),
               "network_requests": 0, "verified_service_associations": 0}
    (args.output / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")
    print(json.dumps(summary, sort_keys=True))


if __name__ == "__main__":
    main()
