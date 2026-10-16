"""Export active and temporarily exhausted jurisdictions and the next search slice."""

import argparse
import csv
import json
import time
from pathlib import Path

from election_data_grabber.discovery_policy import discovery_frontier, search_queue


def read_rows(path):
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8-sig") as stream:
        return list(csv.DictReader(stream))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--registry", type=Path, default=Path("registry"))
    parser.add_argument("--attempts", type=Path, default=Path("audit/local-site-discovery-attempts.csv"))
    parser.add_argument("--watch-state", type=Path, default=Path("watch-data/state.json"))
    parser.add_argument("--output", type=Path, default=Path("watch-data"))
    args = parser.parse_args()
    state = json.loads(args.watch_state.read_text()) if args.watch_state.exists() else {}
    rows = discovery_frontier(read_rows(args.registry / "us_primary_election_localities.csv"),
                              read_rows(args.registry / "local_site_discovery_leads.csv"),
                              read_rows(args.attempts), now=time.time(), watch_state=state)
    args.output.mkdir(parents=True, exist_ok=True)
    for name, selected in [("jurisdiction-discovery-status.csv", rows),
                           ("local-site-search-queue.csv", search_queue(rows))]:
        with (args.output / name).open("w", newline="", encoding="utf-8") as stream:
            writer = csv.DictWriter(stream, fieldnames=list(rows[0]) if rows else [])
            writer.writeheader()
            writer.writerows(selected)


if __name__ == "__main__":
    main()
