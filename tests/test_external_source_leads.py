import pytest

from election_data_grabber.external_source_leads import (
    ExternalLeadOrigin,
    ExternalSourceLead,
    OfficialStatus,
    dedupe_external_leads,
)


def test_multiple_distinct_roles_for_same_url_are_preserved():
    base=dict(
        jurisdiction_id="us:aa:county:x",
        lead_url="https://aa.gov/results",
        origin=ExternalLeadOrigin.RESEARCH_REPOSITORY,
        origin_locator="ElectProject/Early-Vote-2020G:AA",
        official_status=OfficialStatus.THIRD_PARTY_REFERENCE,
    )
    leads=[
        ExternalSourceLead("a",source_role="early_vote",**base),
        ExternalSourceLead("b",source_role="election_night",**base),
    ]
    assert len(dedupe_external_leads(leads))==2


def test_exact_duplicate_is_deduped_without_collapsing_geography():
    lead=ExternalSourceLead(
        "a","us:aa:county:x","https://aa.gov/results",
        ExternalLeadOrigin.SCRAPER_REPOSITORY,"repo/path",
        OfficialStatus.THIRD_PARTY_REFERENCE,source_role="election_night",
    )
    assert len(dedupe_external_leads([lead,lead]))==1


def test_verified_official_from_third_party_requires_verification_note():
    with pytest.raises(ValueError):
        ExternalSourceLead(
            "a","us:aa:county:x","https://aa.gov/results",
            ExternalLeadOrigin.RESEARCH_REPOSITORY,"repo/path",
            OfficialStatus.VERIFIED_OFFICIAL,
        )
