from __future__ import annotations

import csv
from pathlib import Path

TRACKER = Path("registry/us_local_unit_coverage_tracker.csv")

CAPABILITY_FIELDS = (
    "known_final_only",
    "known_election_night_only",
    "known_both",
    "known_units_missing_source",
)
ACCOUNTING_FIELDS = ("enumerated_unresolved",) + CAPABILITY_FIELDS


def validate_row(row: dict[str, str]) -> None:
    expected = int(row["expected_primary_units"])
    accounted = sum(int(row[name]) for name in ACCOUNTING_FIELDS)
    unknown = int(row["estimated_unknown_units"])
    if min(expected, accounted, unknown, *(int(row[name]) for name in ACCOUNTING_FIELDS)) < 0:
        raise ValueError(f"{row['state']}: coverage counts cannot be negative")
    if expected != accounted + unknown:
        raise ValueError(
            f"{row['state']}: invariant failed: expected={expected}, "
            f"accounted={accounted}, unknown={unknown}"
        )


def recompute_unknown(row: dict[str, str]) -> None:
    expected = int(row["expected_primary_units"])
    accounted = sum(int(row[name]) for name in ACCOUNTING_FIELDS)
    row["estimated_unknown_units"] = str(expected - accounted)
    validate_row(row)


def main() -> None:
    with TRACKER.open(encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))

    for row in rows:
        recompute_unknown(row)

    with TRACKER.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)

    expected = sum(int(r["expected_primary_units"]) for r in rows)
    enumerated = sum(sum(int(r[n]) for n in ACCOUNTING_FIELDS) for r in rows)
    unknown = sum(int(r["estimated_unknown_units"]) for r in rows)
    print(f"COVERAGE expected={expected} enumerated={enumerated} unknown={unknown}")


if __name__ == "__main__":
    main()
