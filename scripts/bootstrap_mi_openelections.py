"""Inventory Michigan 2024 precinct files published by OpenElections.

This is a discovery/benchmark utility, not the canonical live source. It establishes
which counties already have normalized historical data and measures distinct precinct
labels and available vote-mode columns.
"""

from __future__ import annotations

import csv
import io
import json
from pathlib import Path

import httpx


API = "https://api.github.com/repos/openelections/openelections-data-mi/contents/2024/counties"
RAW = (
    "https://raw.githubusercontent.com/openelections/openelections-data-mi/"
    "master/2024/counties/{filename}"
)
PREFIX = "20241105__mi__general__"
SUFFIX = "__precinct.csv"
VOTE_MODE_COLUMNS = {
    "election_day",
    "early_voting",
    "absentee",
    "av_counting_boards",
    "provisional",
    "mail",
}


def county_from_filename(filename: str) -> str:
    return filename.removeprefix(PREFIX).removesuffix(SUFFIX)


def main() -> None:
    out = Path("registry/mi_2024_openelections.json")
    out.parent.mkdir(parents=True, exist_ok=True)

    with httpx.Client(timeout=60, follow_redirects=True) as client:
        listing = client.get(API)
        listing.raise_for_status()
        files = [
            item["name"]
            for item in listing.json()
            if item["name"].startswith(PREFIX) and item["name"].endswith(SUFFIX)
        ]

        inventory = []
        for filename in sorted(files):
            response = client.get(RAW.format(filename=filename))
            response.raise_for_status()
            reader = csv.DictReader(io.StringIO(response.text))
            precincts: set[str] = set()
            rows = 0
            for row in reader:
                rows += 1
                precinct = (row.get("precinct") or "").strip()
                if precinct:
                    precincts.add(precinct)
            columns = reader.fieldnames or []
            inventory.append(
                {
                    "county": county_from_filename(filename),
                    "filename": filename,
                    "rows": rows,
                    "distinct_precinct_labels": len(precincts),
                    "vote_mode_columns": sorted(VOTE_MODE_COLUMNS.intersection(columns)),
                    "source_url": RAW.format(filename=filename),
                }
            )

    out.write_text(json.dumps(inventory, indent=2) + "\n")
    print(
        f"Wrote {len(inventory)} counties and "
        f"{sum(x['distinct_precinct_labels'] for x in inventory)} distinct county-scoped "
        f"precinct labels to {out}"
    )


if __name__ == "__main__":
    main()
