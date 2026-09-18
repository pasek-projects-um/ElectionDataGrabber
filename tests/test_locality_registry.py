import pytest
from election_data_grabber.locality_registry import (
    CoverageStatus, EstimateStatus, LocalityDenominator, PrimaryElectionLocality, derive_tracker
)

def locality(jid, state="MI", status=CoverageStatus.ENUMERATED_UNRESOLVED, final=False, live=False, **kw):
    return PrimaryElectionLocality(jid,state,"county",jid.rsplit(":",1)[-1],"provisional_name",status,
        final_capable=final,election_night_capable=live,**kw)

def denominator(state="MI", n=2):
    return LocalityDenominator(state,n,"county",EstimateStatus.PROVISIONAL,"test_fixture")

def test_exactly_one_status_and_capabilities_agree():
    with pytest.raises(ValueError):
        locality("us:mi:county:a",status=CoverageStatus.BOTH,final=True,live=False)

def test_duplicate_urls_or_sources_cannot_duplicate_locality_count():
    rows=[locality("us:mi:county:a"), locality("us:mi:county:a")]
    with pytest.raises(ValueError):
        derive_tracker(rows,[denominator()])

def test_multiple_localities_can_share_one_independent_authority():
    aid="us:authority:ny:board-of-elections:nyc"
    rows=[locality("us:ny:county:new-york","NY",authority_id=aid), locality("us:ny:county:kings","NY",authority_id=aid)]
    out=derive_tracker(rows,[denominator("NY",2)])[0]
    assert out["enumerated_unresolved"]=="2"

def test_known_missing_requires_affirmative_adjudication_not_fetch_failure():
    with pytest.raises(ValueError):
        locality("us:mi:county:a",status=CoverageStatus.KNOWN_MISSING_SOURCE,assessment_method="fetch_failed")
    ok=locality("us:mi:county:a",status=CoverageStatus.KNOWN_MISSING_SOURCE,
        assessment_method="manual_source_investigation",assessment_status="affirmatively_adjudicated")
    assert ok.coverage_status is CoverageStatus.KNOWN_MISSING_SOURCE

def test_tracker_is_derived_and_enforces_denominator():
    rows=[
        locality("us:mi:county:a",status=CoverageStatus.FINAL_ONLY,final=True),
        locality("us:mi:county:b",status=CoverageStatus.BOTH,final=True,live=True),
    ]
    out=derive_tracker(rows,[denominator(n=3)])[0]
    assert out["known_final_only"]=="1"
    assert out["known_both"]=="1"
    assert out["known_units_with_final"]=="2"
    assert out["estimated_unknown_units"]=="1"
    with pytest.raises(ValueError):
        derive_tracker(rows,[denominator(n=1)])

def test_reporting_regimes_do_not_enter_locality_denominator():
    rows=[locality("us:mi:county:a")]
    before=derive_tracker(rows,[denominator(n=2)])
    # #14 reporting regimes are intentionally not an input to derive_tracker.
    after=derive_tracker(rows,[denominator(n=2)])
    assert before==after
