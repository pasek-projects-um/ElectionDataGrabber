"""Extract observed precinct/reporting-unit labels from normalized result files.

This intentionally does not assume that a precinct label is a durable geographic ID.
Each distinct label is scoped to source + election + county. Later crosswalks can connect
labels across elections or to GIS geometries.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path


PRECINCT_FIELDS = (
    "precinct",
    "precinct_name",
    "reporting_unit",
    "reporting_unit_name",
    "ward_precinct",
)


def stable_observation_id(source: str, election: str, county: str, label: str) -> str:
    raw = "\x1f".join([source, election, county, label]).encode()
    return hashlib.sha256(raw).hexdigest()[:20]


def detect_precinct_field(fieldnames: list[str]) -> str | None:
    lower = {f.lower(): f for f in fieldnames}
    for candidate in PRECINCT_FIELDS:
        if candidate in lower:
            return lower[candidate]
    return None


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("files", nargs="+", type=Path)
    parser.add_argument("--source", required=True)
    parser.add_argument("--election", required=True)
    parser.add_argument("--state", required=True)
    parser.add_argument("--out", type=Path, default=Path("registry/observed_precincts.jsonl"))
    args = parser.parse_args()

    args.out.parent.mkdir(parents=True, exist_ok=True)
    observed: dict[tuple[str, str], dict] = {}

    for path in args.files:
        with path.open(newline="", encoding="utf-8-sig") as fh:
            reader = csv.DictReader(fh)
            field = detect_precinct_field(reader.fieldnames or [])
            if not field:
                continue
            for row in reader:
                label = (row.get(field) or "").strip()
                if not label:
                    continue
                county = (row.get("county") or "").strip()
                key = (county, label)
                observed[key] = {
                    "observed_reporting_unit_id": stable_observation_id(
                        args.source, args.election, county, label
                    ),
                    "state": args.state.upper(),
                    "county": county,
                    "election_id": args.election,
                    "source_id": args.source,
                    "raw_label": label,
                    "unit_type": "unknown",
                    "canonical_reporting_unit_id": None,
                    "geometry_id": None,
                }

    with args.out.open("w", encoding="utf-8") as fh:
        for row in sorted(observed.values(), key=lambda x: (x["county"], x["raw_label"])):
            fh.write(json.dumps(row, sort_keys=True) + "\n")

    print(f"Wrote {len(observed)} observed reporting-unit labels to {args.out}")


if __name__ == "__main__":
    main()
