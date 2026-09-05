import csv
from pathlib import Path

def test_michigan_election_night_schema_supports_multiple_source_scopes():
    with Path("registry/mi_election_night_units.csv").open(encoding="utf-8-sig") as f:
        rows=list(csv.DictReader(f))
    assert {r["source_scope"] for r in rows} >= {"county","municipality"}
    required={"election_night_unit_type","unit_completion_observable","vote_mode_at_unit_level","certified_unit_type","night_to_certified_crosswalk"}
    assert required <= set(rows[0])
