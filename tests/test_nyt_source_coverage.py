import csv
from pathlib import Path

def test_nyt_coverage_accounts_for_all_states_and_dc():
    root=Path(__file__).resolve().parents[1]
    with (root/"audit/nyt_2024_state_source_coverage.csv").open(encoding="utf-8",newline="") as f:
        rows=list(csv.DictReader(f))
    assert len(rows)==51
    assert len({r["state"] for r in rows})==51
    assert all(r["nyt_availability"] in {"complete","partial","unusable"} for r in rows)
    assert all(r["source_class"] for r in rows)
