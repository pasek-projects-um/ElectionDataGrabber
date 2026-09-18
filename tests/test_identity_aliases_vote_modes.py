from datetime import date

import pytest

from election_data_grabber.identity_aliases import (
    AliasKind, IdentityAlias, IdentityDecisionStatus, IdentityObjectType,
    authoritative_external_alias, resolve_alias, validate_identity_aliases,
)
from election_data_grabber.models import ResultObservation, VoteMode
from election_data_grabber.vote_modes import (
    VoteModeAggregation, VoteModeMappingStatus, VoteModeRule,
    assert_no_aggregate_component_double_count, normalize_vote_mode, resolve_vote_mode,
)


def alias(canonical, value, *, namespace="name:mi:county", kind=AliasKind.NAME, status=IdentityDecisionStatus.VERIFIED, start=None, end=None):
    return IdentityAlias(
        IdentityObjectType.JURISDICTION, canonical, kind, value, namespace,
        status, 1.0 if status == IdentityDecisionStatus.VERIFIED else None,
        "manual_adjudication", "fixture", "reviewer" if status == IdentityDecisionStatus.VERIFIED else None,
        start, end,
    )


def test_multiple_aliases_resolve_to_one_canonical_identity():
    rows=[alias("us:mi:county:st-joseph","St Joseph"),alias("us:mi:county:st-joseph","St. Joseph")]
    assert resolve_alias(rows,object_type=IdentityObjectType.JURISDICTION,namespace="name:mi:county",value="St. Joseph")=="us:mi:county:st-joseph"


def test_same_name_collision_cannot_be_verified_in_same_namespace_and_period():
    rows=[alias("us:me:municipality:alpha","Washington"),alias("us:me:municipality:beta","Washington")]
    with pytest.raises(ValueError):
        validate_identity_aliases(rows)


def test_rename_and_external_id_adoption_preserve_historical_alias():
    old=alias("us:ct:municipality:example","Old Name",start=date(1900,1,1),end=date(2020,12,31))
    new=alias("us:ct:municipality:example","New Name",start=date(2021,1,1))
    ext=alias("us:ct:municipality:example","09001",namespace="fips",kind=AliasKind.EXTERNAL_ID)
    rows=[old,new,ext]
    assert resolve_alias(rows,object_type=IdentityObjectType.JURISDICTION,namespace="name:mi:county",value="Old Name",when=date(2010,1,1))=="us:ct:municipality:example"
    assert authoritative_external_alias(rows,"us:ct:municipality:example")==ext


def test_ambiguous_or_unreviewed_alias_does_not_auto_merge():
    row=alias("us:me:municipality:x","Springfield",status=IdentityDecisionStatus.AMBIGUOUS)
    assert resolve_alias([row],object_type=IdentityObjectType.JURISDICTION,namespace="name:mi:county",value="Springfield") is None


def test_vote_mode_unknown_stays_unknown_and_raw_label_is_not_convenience_mapped():
    resolution=normalize_vote_mode("mystery counting board",state="MI",source_id="s")
    assert resolution.vote_mode is None
    assert not resolution.recognized


def test_state_override_does_not_leak_across_states():
    assert normalize_vote_mode("AV",state="MI").vote_mode == VoteMode.ABSENTEE
    assert normalize_vote_mode("AV",state="OH").vote_mode is None


def test_source_override_beats_state_and_global_rule():
    rules=[
        VoteModeRule("mail",VoteMode.MAIL,"global","fixture"),
        VoteModeRule("mail",VoteMode.ABSENTEE,"source_override","fixture",state="PA",source_id="pa-source"),
    ]
    assert resolve_vote_mode("mail",rules,state="PA",source_id="pa-source").vote_mode == VoteMode.ABSENTEE
    assert resolve_vote_mode("mail",rules,state="PA",source_id="other").vote_mode == VoteMode.MAIL


def test_candidate_mapping_never_promotes():
    rules=[VoteModeRule("AV",VoteMode.ABSENTEE,"candidate","fixture",status=VoteModeMappingStatus.CANDIDATE,state="ME")]
    assert resolve_vote_mode("AV",rules,state="ME").vote_mode is None


def _obs(mode):
    from datetime import datetime
    return ResultObservation(election_id="2024-general",jurisdiction_id="us:pa:county:x",reporting_unit_id="p1",reporting_unit_name="P1",contest_name="Mayor",choice_name="A",votes=1,vote_mode=mode,source_id="s",fetched_at=datetime(2024,1,1))


def test_aggregate_total_and_components_require_explicit_aggregation_basis():
    with pytest.raises(ValueError):
        assert_no_aggregate_component_double_count([_obs(VoteMode.TOTAL),_obs(VoteMode.MAIL)])
    assert_no_aggregate_component_double_count([_obs(VoteMode.MAIL),_obs(VoteMode.ELECTION_DAY)])
