"""Merge observed discovery batches into a reviewable source-lead catalog."""

import argparse
import csv
import json
from pathlib import Path

from election_data_grabber.discovery_catalog import catalog_sources, write_catalog


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--batch", action="append", nargs=2, metavar=("CHECKPOINT", "SEEDS"), required=True
    )
    parser.add_argument("--observed-date", required=True)
    parser.add_argument(
        "--output", type=Path, default=Path("registry/discovered_result_sources.csv")
    )
    parser.add_argument(
        "--summary", type=Path, default=Path("audit/dashboard-discovery/catalog-summary.json")
    )
    args = parser.parse_args()
    batches = []
    for checkpoint, seeds in args.batch:
        with open(seeds, newline="", encoding="utf-8-sig") as stream:
            batches.append((json.loads(Path(checkpoint).read_text()), list(csv.DictReader(stream))))
    rows = catalog_sources(batches, observed_date=args.observed_date)
    summary = write_catalog(rows, args.output)
    args.summary.parent.mkdir(parents=True, exist_ok=True)
    args.summary.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
