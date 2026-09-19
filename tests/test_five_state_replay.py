from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pytest

from election_data_grabber.identity_aliases import (
    AliasKind,
    IdentityAlias,
    IdentityDecisionStatus,
    IdentityObjectType,
)
from election_data_grabber.models import (
    ReportingProgress,
    ReportingProgressBasis,
    ReportingProgressKind,
    ReportingProgressScope,
    UpdateSemantics,
    VoteMode,
)
from election_data_grabber.replay import (
    ReplayFixture,
    persist_replay_output,
    replay_fixture,
    snapshot_for_fixture,
    validate_replay_identity,
)
from election_data_grabber.reporting_unit_identity import UnitType
from election_data_grabber.source_capabilities import CapabilityType, VerificationStatus


NOW=datetime(2026,11,3,22,0,tzinfo=timezone.utc)
ROOT=Path(__file__).parent/"fixtures"/"replay"


CASES=[
    ReplayFixture("MI","2026-general","us:mi:county:washtenaw","us:authority:mi:county-clerk:washtenaw-county-clerk","replay-mi",CapabilityType.ELECTION_NIGHT,"election-night","csv",ROOT/"mi.csv",NOW,"https://example.gov/mi"),
    ReplayFixture("OH","2026-general","us:oh:county:franklin","us:authority:oh:board-of-elections:franklin-county-board-of-elections","replay-oh",CapabilityType.FINAL,"certified","json",ROOT/"oh.json",NOW,"https://example.gov/oh"),
    ReplayFixture("CT","2026-general","us:ct:town:greenwich","us:authority:ct:town-clerk:greenwich-town-clerk","replay-ct",CapabilityType.FINAL,"certified","csv",ROOT/"ct.csv",NOW,"https://example.gov/ct"),
    ReplayFixture("PA","2026-general","us:pa:county:philadelphia","us:authority:pa:county-election-office:philadelphia-county-election-office","replay-pa",CapabilityType.ELECTION_NIGHT,"election-night","csv",ROOT/"pa.csv",NOW,"https://example.gov/pa"),
    ReplayFixture("ME","2026-general","us:me:municipality:portland","us:authority:me:municipal-clerk:portland-municipal-clerk","replay-me",CapabilityType.FINAL,"certified","json",ROOT/"me.json",NOW,"https://example.gov/me",UnitType.WARD),
]


@pytest.mark.parametrize("fixture",CASES,ids=lambda f:f.state)
def test_identical_snapshot_replay_is_deterministic_and_traceable(fixture):
    a=replay_fixture(fixture)
    b=replay_fixture(fixture)
    assert a == b
    snapshot=snapshot_for_fixture(fixture)
    assert a.observations
    assert all(row["source_id"] == fixture.source_id for row in a.observations)
    assert all(row["snapshot_sha256"] == snapshot.sha256 for row in a.observations)


def test_source_order_does_not_become_ballot_order():
    out=replay_fixture(CASES[1])
    assert sorted(row["source_order"] for row in out.observations) == [1,2]
    assert all(row["ballot_order"] is None for row in out.observations)


def test_reporting_topology_and_final_vs_live_regime_survive_replay():
    mi=replay_fixture(CASES[0])
    me=replay_fixture(CASES[4])
    assert all(":regime:election-night:" in row["reporting_regime_id"] for row in mi.observations)
    assert all(":regime:certified:" in row["reporting_regime_id"] for row in me.observations)
    assert all("reporting-unit:ward:" in row["reporting_unit_id"] for row in me.observations)
    assert all(row["jurisdiction_id"] == "us:me:municipality:portland" for row in me.observations)


def test_raw_and_canonical_vote_mode_semantics_survive():
    mi=replay_fixture(CASES[0])
    pa=replay_fixture(CASES[3])
    assert {row["raw_vote_mode"] for row in mi.observations} == {"av"}
    assert {row["vote_mode"] for row in mi.observations} == {VoteMode.ABSENTEE.value}
    assert {row["raw_vote_mode"] for row in pa.observations} == {"mail"}
    assert {row["vote_mode"] for row in pa.observations} == {VoteMode.MAIL.value}


def test_ambiguous_identity_is_not_silently_accepted():
    aliases=[
        IdentityAlias(
            IdentityObjectType.JURISDICTION,"us:me:municipality:portland-a",AliasKind.NAME,
            "Portland","fixture",IdentityDecisionStatus.AMBIGUOUS,None,"fixture","fixture",
        )
    ]
    with pytest.raises(ValueError,match="identity unresolved or ambiguous"):
        validate_replay_identity(
            aliases,object_type=IdentityObjectType.JURISDICTION,namespace="fixture",value="Portland"
        )


def test_integrity_failure_stops_persistence(tmp_path):
    fixture=ReplayFixture(
        "MI","2026-general","us:mi:county:washtenaw","us:authority:mi:county-clerk:washtenaw-county-clerk",
        "replay-mi",CapabilityType.ELECTION_NIGHT,"election-night","csv",ROOT/"mi.csv",NOW,"https://example.gov/mi",
    )
    snapshot=snapshot_for_fixture(fixture)
    progress=[
        ReportingProgress(
            election_id=fixture.election_id,jurisdiction_id=fixture.jurisdiction_id,
            source_id=fixture.source_id,fetched_at=NOW,
            scope=ReportingProgressScope.SOURCE,
            kind=ReportingProgressKind.SOURCE_COUNTS,
            basis=ReportingProgressBasis.SOURCE_REPORTED,
            update_semantics=UpdateSemantics.CUMULATIVE,
            reporting_count=9,expected_count=10,
            snapshot_sha256=snapshot.sha256,raw_status="9/10",
        ),
        ReportingProgress(
            election_id=fixture.election_id,jurisdiction_id=fixture.jurisdiction_id,
            source_id=fixture.source_id,fetched_at=NOW.replace(minute=1),
            scope=ReportingProgressScope.SOURCE,
            kind=ReportingProgressKind.SOURCE_COUNTS,
            basis=ReportingProgressBasis.SOURCE_REPORTED,
            update_semantics=UpdateSemantics.CUMULATIVE,
            reporting_count=8,expected_count=10,
            snapshot_sha256=snapshot.sha256,raw_status="8/10",
        ),
    ]
    with pytest.raises(ValueError,match="reporting progress integrity failed"):
        output=replay_fixture(fixture,progress=progress)
        persist_replay_output(tmp_path,output)
    assert not (tmp_path/"canonical_replay.json").exists()


def test_progress_is_included_in_deterministic_output():
    fixture=CASES[0]
    snapshot=snapshot_for_fixture(fixture)
    progress=[
        ReportingProgress(
            election_id=fixture.election_id,jurisdiction_id=fixture.jurisdiction_id,
            source_id=fixture.source_id,fetched_at=NOW,
            scope=ReportingProgressScope.SOURCE,
            kind=ReportingProgressKind.SOURCE_COUNTS,
            basis=ReportingProgressBasis.SOURCE_REPORTED,
            update_semantics=UpdateSemantics.CUMULATIVE,
            reporting_count=4,expected_count=10,
            snapshot_sha256=snapshot.sha256,raw_status="4/10",
        )
    ]
    a=replay_fixture(fixture,progress=progress)
    b=replay_fixture(fixture,progress=progress)
    assert a == b
    assert a.progress[0]["reporting_count"] == 4



def test_candidate_source_capability_is_not_accepted_for_replay():
    fixture=ReplayFixture(
        "PA","2026-general","us:pa:county:philadelphia",
        "us:authority:pa:county-election-office:philadelphia-county-election-office",
        "replay-pa",CapabilityType.ELECTION_NIGHT,"election-night","csv",ROOT/"pa.csv",NOW,
        "https://example.gov/pa",verification_status=VerificationStatus.CANDIDATE,
    )
    with pytest.raises(ValueError,match="positively adjudicated"):
        replay_fixture(fixture)



def test_replay_can_pin_expected_fixture_sha():
    fixture=CASES[0]
    snapshot=snapshot_for_fixture(fixture)
    assert replay_fixture(fixture,expected_snapshot_sha256=snapshot.sha256).observations
    with pytest.raises(ValueError,match="expected immutable snapshot"):
        replay_fixture(fixture,expected_snapshot_sha256="0"*64)
