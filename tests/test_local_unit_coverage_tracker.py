import csv
from pathlib import Path

from scripts.update_local_unit_coverage_tracker import recompute_unknown, validate_row


def row(**overrides):
    base = {
        "state": "XX",
        "expected_primary_units": "10",
        "enumerated_unresolved": "0",
        "known_final_only": "0",
        "known_election_night_only": "0",
        "known_both": "0",
        "known_units_missing_source": "0",
        "estimated_unknown_units": "10",
    }
    base.update({k: str(v) for k, v in overrides.items()})
    return base


def test_enumerated_unresolved_reduces_unknown():
    r = row(enumerated_unresolved=3)
    recompute_unknown(r)
    assert r["estimated_unknown_units"] == "7"
    validate_row(r)


def test_capability_buckets_are_mutually_accounted():
    r = row(known_final_only=2, known_election_night_only=1, known_both=3, known_units_missing_source=1)
    recompute_unknown(r)
    assert r["estimated_unknown_units"] == "3"


def test_tracker_file_obeys_invariant():
    path = Path("registry/us_local_unit_coverage_tracker.csv")
    with path.open(encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            validate_row(r)
