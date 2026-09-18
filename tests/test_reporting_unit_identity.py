from datetime import date

import pytest

from election_data_grabber.reporting_unit_identity import (
    AggregationScope,
    AllocationSemantics,
    CanonicalReportingUnit,
    IdentityStatus,
    ReconciliationStatus,
    RelationshipType,
    ReportingUnitCrosswalk,
    reporting_regime_id,
    reporting_unit_id,
    validate_reporting_unit_crosswalks,
    UnitType,
)

SHA = "a" * 64


def rid(jurisdiction, election, regime, raw, native=""):
    return reporting_unit_id("MI", election, regime, UnitType.PRECINCT, raw, native)


def test_same_name_different_jurisdictions_and_elections_do_not_collide():
    r1 = reporting_regime_id("us:mi:county:washtenaw", "2024-general", "election-night", "enhanced")
    r2 = reporting_regime_id("us:mi:county:wayne", "2024-general", "election-night", "enhanced")
    assert rid("washtenaw", "2024-general", r1, "Precinct 1") != rid("wayne", "2024-general", r2, "Precinct 1")
    assert rid("washtenaw", "2024-general", r1, "Precinct 1") != rid("washtenaw", "2022-general", r1, "Precinct 1")


def test_source_native_identifier_is_preserved_and_required_for_authoritative_status():
    regime = reporting_regime_id("us:oh:county:franklin", "2024-general", "certified", "boe")
    unit_id = reporting_unit_id("OH", "2024-general", regime, UnitType.PRECINCT, "Pct 001", "0001")
    unit = CanonicalReportingUnit(
        unit_id, "2024-general", "us:oh:county:franklin",
        "us:authority:oh:board-of-elections:franklin", "boe", "final", regime,
        UnitType.PRECINCT, "Precinct 1", "Pct 001", SHA, "0001",
        aggregation_scope=AggregationScope.PRECINCT,
        allocation_semantics=AllocationSemantics.NATIVE_TO_PRECINCT,
        identity_status=IdentityStatus.AUTHORITATIVE_SOURCE_NATIVE,
    )
    assert unit.source_native_id == "0001"
    assert unit.identity_status != unit.reconciliation_status


def test_rename_split_merge_and_aggregate_crosswalks_are_not_identity_reuse():
    old, new, child = "ru:old", "ru:new", "ru:child"
    rows = [
        ReportingUnitCrosswalk(old, new, RelationshipType.RENAMED_TO, "certified", SHA, effective_from=date(2024, 1, 1)),
        ReportingUnitCrosswalk(new, child, RelationshipType.SPLIT_INTO, "redistricting", SHA),
        ReportingUnitCrosswalk("ru:avcb", new, RelationshipType.AGGREGATES, "election-night", SHA),
    ]
    validate_reporting_unit_crosswalks(rows)
    assert {r.relationship_type for r in rows} == {RelationshipType.RENAMED_TO, RelationshipType.SPLIT_INTO, RelationshipType.AGGREGATES}


def test_non_geographic_counting_unit_does_not_require_fake_precinct():
    regime = reporting_regime_id("us:mi:county:washtenaw", "2024-general", "election-night", "vendor")
    unit = CanonicalReportingUnit(
        reporting_unit_id("MI", "2024-general", regime, UnitType.MULTI_PRECINCT_AVCB, "AVCB 7"),
        "2024-general", "us:mi:county:washtenaw",
        "us:authority:mi:county-clerk:washtenaw", "vendor", "election_night", regime,
        UnitType.MULTI_PRECINCT_AVCB, "AVCB 7", "AVCB 7", SHA,
        aggregation_scope=AggregationScope.MULTI_PRECINCT,
        allocation_semantics=AllocationSemantics.SOURCE_NATIVE_NON_GEOGRAPHIC,
    )
    assert unit.parent_reporting_unit_id is None


def test_weight_requires_evidence_basis_and_temporal_ranges_validate():
    with pytest.raises(ValueError):
        ReportingUnitCrosswalk("a", "b", RelationshipType.APPROXIMATE_CROSSWALK, "source", SHA, weight=.5)
    with pytest.raises(ValueError):
        ReportingUnitCrosswalk("a", "b", RelationshipType.SAME_AS, "source", SHA, effective_from=date(2025,1,1), effective_to=date(2024,1,1))


def test_duplicate_crosswalk_fails_validation():
    row = ReportingUnitCrosswalk("a", "b", RelationshipType.COMPONENT_OF, "source", SHA)
    with pytest.raises(ValueError):
        validate_reporting_unit_crosswalks([row, row])
