from election_data_grabber.external_lead_extractor import (
    classify_candidate_url,
    extract_http_urls,
    leads_from_repository_text,
)
from election_data_grabber.external_source_leads import OfficialStatus


def test_extract_urls_dedupes_and_trims_punctuation():
    text="See https://elections.example.gov/results.csv, then https://elections.example.gov/results.csv."
    assert extract_http_urls(text)==["https://elections.example.gov/results.csv"]


def test_gov_host_is_only_likely_official_until_verified():
    assert classify_candidate_url("https://elections.example.gov/results") == OfficialStatus.LIKELY_OFFICIAL


def test_repository_extraction_retains_origin_locator():
    leads=leads_from_repository_text(
        "source=https://elections.example.gov/results",
        source_record_prefix="electproject-2020-aa",
        origin_locator="ElectProject/Early-Vote-2020G:AA.py",
        jurisdiction_id="us:aa",
        source_role="early_vote",
    )
    assert len(leads)==1
    assert leads[0].origin_locator=="ElectProject/Early-Vote-2020G:AA.py"
    assert leads[0].jurisdiction_id=="us:aa"
    assert leads[0].official_status == OfficialStatus.LIKELY_OFFICIAL
