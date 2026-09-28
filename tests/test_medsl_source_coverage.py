import csv
from pathlib import Path

def test_medsl_source_leads_cover_all_states_and_dc():
    root=Path(__file__).resolve().parents[1]
    with (root/"audit/medsl_2024_source_leads.csv").open(encoding="utf-8",newline="") as f:
        rows=list(csv.DictReader(f))
    assert len(rows)==51
    assert len({r["state"] for r in rows})==51
    assert all(r["source_url"] for r in rows)
    assert all(r["source_class"] for r in rows)

def test_medsl_package_coverage_matches_source_coverage():
    root=Path(__file__).resolve().parents[1]
    def states(path):
        with path.open(encoding="utf-8",newline="") as f:
            return {r["state"] for r in csv.DictReader(f)}
    assert states(root/"audit/medsl_2024_source_leads.csv")==states(root/"audit/medsl_2024_state_package_coverage.csv")
