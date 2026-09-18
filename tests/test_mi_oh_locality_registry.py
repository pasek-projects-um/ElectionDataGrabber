import csv
from pathlib import Path

from election_data_grabber.locality_registry import derive_tracker, read_denominators, read_localities
from election_data_grabber.authority_identity import AuthorityJurisdictionCrosswalk, validate_crosswalks

ROOT=Path(__file__).resolve().parents[1]

def test_mi_oh_canonical_locality_population_is_complete_and_unique():
    rows=read_localities(ROOT/"registry/us_primary_election_localities.csv")
    mi=[r for r in rows if r.state=="MI"]; oh=[r for r in rows if r.state=="OH"]
    assert len(mi)==83
    assert len(oh)==88
    assert len({r.jurisdiction_id for r in mi+oh})==171
    assert all(r.authority_id.startswith("us:authority:") for r in mi+oh)

def test_mi_oh_denominators_are_fully_enumerated_from_ids():
    rows=read_localities(ROOT/"registry/us_primary_election_localities.csv")
    den=read_denominators(ROOT/"registry/us_primary_election_locality_denominators.csv")
    tracker={r["state"]:r for r in derive_tracker(rows,den)}
    assert tracker["MI"]["expected_primary_units"]=="83"
    assert tracker["MI"]["estimated_unknown_units"]=="0"
    assert tracker["OH"]["expected_primary_units"]=="88"
    assert tracker["OH"]["estimated_unknown_units"]=="0"

def test_committed_tracker_equals_derived_tracker():
    rows=read_localities(ROOT/"registry/us_primary_election_localities.csv")
    den=read_denominators(ROOT/"registry/us_primary_election_locality_denominators.csv")
    derived=derive_tracker(rows,den)
    with (ROOT/"registry/us_local_unit_coverage_tracker.csv").open(encoding="utf-8-sig") as f:
        committed=list(csv.DictReader(f))
    assert committed==derived

def test_mi_oh_authority_crosswalks_are_valid_and_cover_every_locality():
    rows=read_localities(ROOT/"registry/us_primary_election_localities.csv")
    wanted={r.jurisdiction_id for r in rows if r.state in {"MI","OH"}}
    with (ROOT/"registry/authority_jurisdiction_crosswalk.csv").open(encoding="utf-8-sig") as f:
        raw=list(csv.DictReader(f))
    cross=[AuthorityJurisdictionCrosswalk(r["authority_id"],r["jurisdiction_id"],evidence_url=r["evidence_url"] or None) for r in raw]\n    mi_oh_cross=[r for r in cross if r.jurisdiction_id.startswith(("us:mi:", "us:oh:"))]
    validate_crosswalks(cross)
    assert {r.jurisdiction_id for r in mi_oh_cross}==wanted
