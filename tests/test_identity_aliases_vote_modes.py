from datetime import date, datetime, timezone

import pytest

from election_data_grabber.adapters.enhanced_voting import parse_enhanced_voting_html
from election_data_grabber.adapters.generic_csv import parse_generic_precinct_csv
from election_data_grabber.identity_aliases import (
    AliasKind, IdentityAlias, IdentityDecisionStatus, IdentityObjectType,
    authoritative_external_alias, merge_identity_aliases, read_identity_aliases,
    resolve_alias, validate_identity_aliases, write_identity_aliases,
)
from election_data_grabber.models import ResultObservation, VoteMode
from election_data_grabber.vote_modes import (
    VoteModeMappingStatus, VoteModeRule,
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


def test_generic_csv_mi_av_uses_state_governance_and_carries_provenance():
    body=b"precinct,office,candidate,av,total\nP1,Mayor,Alice,7,10\n"
    rows=parse_generic_precinct_csv(
        body,election_id="e",jurisdiction_id="us:mi:county:washtenaw",source_id="mi-source",
        fetched_at=datetime(2026,8,4,tzinfo=timezone.utc),
    )
    av=next(r for r in rows if r.raw_vote_mode=="av")
    assert av.vote_mode==VoteMode.ABSENTEE
    assert av.vote_mode_mapping_method=="state_semantic_override"
    assert av.vote_mode_evidence_reference=="mi_av_semantics"


def test_generic_csv_oh_av_remains_unknown():
    body=b"precinct,office,candidate,av,total\nP1,Mayor,Alice,7,10\n"
    rows=parse_generic_precinct_csv(
        body,election_id="e",jurisdiction_id="us:oh:county:franklin",source_id="oh-source",
        fetched_at=datetime(2026,11,3,tzinfo=timezone.utc),
    )
    av=next(r for r in rows if r.raw_vote_mode=="av")
    assert av.vote_mode==VoteMode.UNKNOWN
    assert av.vote_mode_mapping_method is None


def test_enhanced_voting_pa_literal_modes_carry_governed_provenance():
    import json
    payload={"results":[{"precinctName":"P1","contestName":"Mayor","candidateName":"Alice","mail":4,"total":9}]}
    html=f'<script type="application/json">{json.dumps(payload)}</script>'.encode()
    rows=parse_enhanced_voting_html(
        html,election_id="e",jurisdiction_id="us:pa:county:allegheny",source_id="pa-enhanced",
        fetched_at=datetime(2026,11,3,tzinfo=timezone.utc),
    )
    mail=next(r for r in rows if r.raw_vote_mode=="mail")
    assert mail.vote_mode==VoteMode.MAIL
    assert mail.vote_mode_mapping_method=="literal_label"


def test_maine_document_label_not_governed_without_evidence():
    resolution=normalize_vote_mode("Absentee / UOCAVA combined",state="ME",source_id="me-document")
    assert resolution.vote_mode is None


def _obs(mode):
    return ResultObservation(election_id="2024-general",jurisdiction_id="us:pa:county:x",reporting_unit_id="p1",reporting_unit_name="P1",contest_name="Mayor",choice_name="A",votes=1,vote_mode=mode,source_id="s",fetched_at=datetime(2024,1,1))


def test_aggregate_total_and_components_require_explicit_aggregation_basis():
    with pytest.raises(ValueError):
        assert_no_aggregate_component_double_count([_obs(VoteMode.TOTAL),_obs(VoteMode.MAIL)])
    assert_no_aggregate_component_double_count([_obs(VoteMode.MAIL),_obs(VoteMode.ELECTION_DAY)])


def test_identity_alias_registry_round_trips_and_reruns_idempotently(tmp_path):
    registry=tmp_path/"identity_aliases.csv"
    old=alias("us:ct:municipality:example","Old Name",start=date(1900,1,1),end=date(2020,12,31))
    ext=alias("us:ct:municipality:example","09001",namespace="fips",kind=AliasKind.EXTERNAL_ID)
    rows=merge_identity_aliases([], [old, ext])
    write_identity_aliases(registry, rows)
    first=registry.read_bytes()

    loaded=read_identity_aliases(registry)
    rerun=merge_identity_aliases(loaded, [old, ext])
    write_identity_aliases(registry, rerun)

    assert registry.read_bytes()==first
    assert set(read_identity_aliases(registry))==set(rows)


def test_alias_registry_cannot_silently_repoint_authoritative_external_id(tmp_path):
    registry=tmp_path/"identity_aliases.csv"
    ext=alias("us:ct:municipality:example","09001",namespace="fips",kind=AliasKind.EXTERNAL_ID)
    write_identity_aliases(registry,[ext])
    conflicting=alias("us:ct:municipality:other","09001",namespace="fips",kind=AliasKind.EXTERNAL_ID)
    with pytest.raises(ValueError):
        write_identity_aliases(registry,merge_identity_aliases(read_identity_aliases(registry),[conflicting]))


def test_authoritative_external_alias_requires_unique_namespace_or_value():
    fips=alias("us:ct:municipality:example","09001",namespace="fips",kind=AliasKind.EXTERNAL_ID)
    state_id=alias("us:ct:municipality:example","EXAMPLE-1",namespace="ct:sots",kind=AliasKind.EXTERNAL_ID)
    assert authoritative_external_alias([fips,state_id],"us:ct:municipality:example") is None
    assert authoritative_external_alias([fips,state_id],"us:ct:municipality:example",namespace="fips")==fips


def test_state_only_and_source_only_conflict_is_unresolved_without_combined_override():
    rules=[
        VoteModeRule("AV",VoteMode.ABSENTEE,"state","fixture",state="MI"),
        VoteModeRule("AV",VoteMode.MAIL,"source","fixture",source_id="vendor"),
    ]
    assert resolve_vote_mode("AV",rules,state="MI",source_id="vendor").vote_mode is None
    rules.append(VoteModeRule("AV",VoteMode.ABSENTEE,"combined","fixture",state="MI",source_id="vendor"))
    assert resolve_vote_mode("AV",rules,state="MI",source_id="vendor").vote_mode==VoteMode.ABSENTEE


def test_double_count_guard_is_snapshot_scoped():
    a=_obs(VoteMode.TOTAL).model_copy(update={"snapshot_sha256":"a"*64})
    b=_obs(VoteMode.MAIL).model_copy(update={"snapshot_sha256":"b"*64})
    assert_no_aggregate_component_double_count([a,b])


def test_generic_json_mi_av_uses_state_governance():
    from election_data_grabber.adapters.generic_json import parse_generic_results_json
    payload={"reporting_units":[{"id":"p1","name":"P1","contests":[{"name":"Mayor","choices":[{"name":"Alice","votes":7,"mode":"AV"}]}]}]}
    row=parse_generic_results_json(
        payload,election_id="e",jurisdiction_id="us:mi:county:washtenaw",source_id="mi-json",
        fetched_at=datetime(2026,8,4,tzinfo=timezone.utc),
    )[0]
    assert row.vote_mode==VoteMode.ABSENTEE
    assert row.vote_mode_mapping_method=="state_semantic_override"


def test_temporal_alias_requires_as_of_date():
    old=alias("us:ct:municipality:old","Shared Name",start=date(1900,1,1),end=date(2020,12,31))
    new=alias("us:ct:municipality:new","Shared Name",start=date(2021,1,1))
    rows=[old,new]
    assert resolve_alias(rows,object_type=IdentityObjectType.JURISDICTION,namespace="name:mi:county",value="Shared Name") is None
    assert resolve_alias(rows,object_type=IdentityObjectType.JURISDICTION,namespace="name:mi:county",value="Shared Name",when=date(2010,1,1))=="us:ct:municipality:old"
    assert resolve_alias(rows,object_type=IdentityObjectType.JURISDICTION,namespace="name:mi:county",value="Shared Name",when=date(2024,1,1))=="us:ct:municipality:new"


def test_rerun_cannot_downgrade_verified_alias():
    verified=alias("us:mi:county:x","Example")
    proposed=alias("us:mi:county:x","Example",status=IdentityDecisionStatus.PROPOSED)
    with pytest.raises(ValueError):
        merge_identity_aliases([verified],[proposed])


def test_non_overlapping_historical_decision_does_not_downgrade_current_alias():
    historical=alias(
        "us:mi:county:x","Example",status=IdentityDecisionStatus.PROPOSED,
        start=date(1900,1,1),end=date(1999,12,31),
    )
    current=alias("us:mi:county:x","Example",start=date(2000,1,1))
    merged=merge_identity_aliases([current],[historical])
    assert historical in merged and current in merged
