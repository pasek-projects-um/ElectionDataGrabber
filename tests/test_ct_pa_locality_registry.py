import csv
from pathlib import Path
from election_data_grabber.locality_registry import derive_tracker, read_denominators, read_localities

ROOT=Path(__file__).resolve().parents[1]

def test_ct_pa_rollout_counts_and_identity_levels():
    rows=read_localities(ROOT/"registry/us_primary_election_localities.csv")
    ct=[r for r in rows if r.state=="CT"]; pa=[r for r in rows if r.state=="PA"]
    assert len(ct)==169 and {r.jurisdiction_level for r in ct}=={"municipality"}
    assert len(pa)==67 and {r.jurisdiction_level for r in pa}=={"county"}
    assert len({r.jurisdiction_id for r in ct+pa})==236

def test_ct_historical_counties_do_not_become_denominator_units():
    rows=read_localities(ROOT/"registry/us_primary_election_localities.csv")
    ct=[r for r in rows if r.state=="CT"]
    assert all(r.coverage_status.value=="enumerated_unresolved" for r in ct)
    assert all("Historical county=" in r.notes and "current planning region=" in r.notes for r in ct)

def test_pa_state_bulk_establishes_final_floor_without_inventing_live_capability():
    rows=read_localities(ROOT/"registry/us_primary_election_localities.csv")
    pa=[r for r in rows if r.state=="PA"]
    assert all(r.final_capable for r in pa)
    live=[r.canonical_name for r in pa if r.election_night_capable]
    assert live==["Philadelphia"]

def test_ct_pa_fully_enumerate_denominators_and_tracker_is_reproducible():
    rows=read_localities(ROOT/"registry/us_primary_election_localities.csv")
    den=read_denominators(ROOT/"registry/us_primary_election_locality_denominators.csv")
    derived=derive_tracker(rows,den); by={r["state"]:r for r in derived}
    assert by["CT"]["expected_primary_units"]=="169" and by["CT"]["estimated_unknown_units"]=="0"
    assert by["PA"]["expected_primary_units"]=="67" and by["PA"]["estimated_unknown_units"]=="0"
    with (ROOT/"registry/us_local_unit_coverage_tracker.csv").open(encoding="utf-8-sig") as f:
        committed=list(csv.DictReader(f))
    assert committed==derived
