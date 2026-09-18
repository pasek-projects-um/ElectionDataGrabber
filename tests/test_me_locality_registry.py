import csv
from pathlib import Path


def _rows(path):
    with Path(path).open(encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def test_maine_registry_has_unique_matching_localities():
    authorities=_rows("registry/me_locality_authorities.csv")
    capabilities=_rows("registry/me_locality_capabilities.csv")
    a={r["locality"] for r in authorities}
    c={r["locality"] for r in capabilities}
    assert len(authorities) == len(a)
    assert len(capabilities) == len(c)
    assert len(a) >= 100
    assert a == c


def test_maine_canonical_rollout_and_denominator_boundary():
    from election_data_grabber.locality_registry import derive_tracker, read_denominators, read_localities
    rows=read_localities(Path("registry/us_primary_election_localities.csv"))
    me=[r for r in rows if r.state=="ME"]
    assert len(me)==350
    assert len({r.jurisdiction_id for r in me})==350
    assert {r.jurisdiction_level for r in me}=={"municipality"}
    assert all("wards/precincts/reporting units are excluded" in r.notes for r in me)
    assert sum(r.coverage_status.value=="final_only" for r in me)==150
    assert sum(r.coverage_status.value=="enumerated_unresolved" for r in me)==200
    assert not any(r.election_night_capable for r in me)
    den=read_denominators(Path("registry/us_primary_election_locality_denominators.csv"))
    derived=derive_tracker(rows,den); by={r["state"]:r for r in derived}
    assert by["ME"]["expected_primary_units"]=="350"
    assert by["ME"]["estimated_unknown_units"]=="0"
    assert _rows("registry/us_local_unit_coverage_tracker.csv")==derived
