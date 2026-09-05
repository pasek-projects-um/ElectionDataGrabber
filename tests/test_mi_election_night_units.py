import csv
from pathlib import Path

def test_michigan_election_night_schema_is_county_only_for_current_pass():
    with Path("registry/mi_election_night_units.csv").open(encoding="utf-8-sig") as f:
        rows=list(csv.DictReader(f))
    assert len(rows) == 83
    assert {r["source_scope"] for r in rows} == {"county"}
    required={"election_night_unit_type","unit_completion_observable","vote_mode_at_unit_level","certified_unit_type","night_to_certified_crosswalk"}
    assert required <= set(rows[0])
