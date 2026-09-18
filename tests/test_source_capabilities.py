from pathlib import Path
import csv
from election_data_grabber.locality_registry import read_localities, read_denominators, derive_tracker
from election_data_grabber.source_capabilities import CapabilityType, JurisdictionSourceCapability, derived_capabilities, read_source_capabilities, validate_source_capabilities, validate_locality_bindings

ROOT=Path(__file__).resolve().parents[1]

def test_source_capability_registry_reproduces_positive_locality_capability():
    localities=read_localities(ROOT/"registry/us_primary_election_localities.csv")
    caps=read_source_capabilities(ROOT/"registry/jurisdiction_source_capabilities.csv")
    validate_locality_bindings(caps, localities)
    derived=derived_capabilities(caps)
    for r in localities:
        assert derived.get(r.jurisdiction_id,(False,False)) == (r.final_capable,r.election_night_capable)

def test_multiple_sources_do_not_change_locality_denominator():
    a=JurisdictionSourceCapability("us:mi:county:a","us:authority:mi:county-clerk:a","one",CapabilityType.FINAL,verification_status="verified",assessment_method="fixture",evidence_reference="fixture")
    b=JurisdictionSourceCapability("us:mi:county:a","us:authority:mi:county-clerk:a","two",CapabilityType.ELECTION_NIGHT,verification_status="verified",assessment_method="fixture",evidence_reference="fixture")
    assert derived_capabilities([a,b])["us:mi:county:a"] == (True,True)

def test_unverified_source_evidence_cannot_promote_capability():
    r=JurisdictionSourceCapability("us:ct:municipality:a","us:authority:ct:town-clerk:a","candidate",CapabilityType.ELECTION_NIGHT,verification_status="candidate",assessment_method="discovery",evidence_reference="fixture")
    assert "us:ct:municipality:a" not in derived_capabilities([r])

def test_five_state_tracker_is_exact_generated_output():
    loc=read_localities(ROOT/"registry/us_primary_election_localities.csv")
    den=read_denominators(ROOT/"registry/us_primary_election_locality_denominators.csv")
    derived=derive_tracker(loc,den)
    with (ROOT/"registry/us_local_unit_coverage_tracker.csv").open(encoding="utf-8-sig",newline="") as f:
        committed=list(csv.DictReader(f))
    assert committed == derived
    five=[r for r in loc if r.state in {"MI","OH","CT","PA","ME"}]
    assert len(five)==757
    assert len({r.jurisdiction_id for r in five})==757


def test_same_legacy_source_can_expose_final_and_live_capabilities():
    caps=read_source_capabilities(ROOT/"registry/jurisdiction_source_capabilities.csv")
    pairs={}
    for r in caps:
        pairs.setdefault((r.jurisdiction_id,r.source_id),set()).add(r.capability_type)
    assert any(v == {CapabilityType.FINAL, CapabilityType.ELECTION_NIGHT} for v in pairs.values())


def test_capability_requires_provenance_and_valid_interval():
    import pytest
    with pytest.raises(ValueError):
        JurisdictionSourceCapability("us:mi:county:a","us:authority:mi:county-clerk:a","one",CapabilityType.FINAL,verification_status="verified",assessment_method="fixture")
    with pytest.raises(ValueError):
        JurisdictionSourceCapability("us:mi:county:a","us:authority:mi:county-clerk:a","one",CapabilityType.FINAL,valid_from="2026-12-01",valid_to="2026-01-01",verification_status="verified",assessment_method="fixture",evidence_reference="fixture")
