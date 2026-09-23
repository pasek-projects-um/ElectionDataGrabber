from election_data_grabber.easy_ingest import build_candidates, ingest_tier, summarize

def test_result_links_are_fingerprinted_individually_and_deduped():
    rows=[
        {"state":"GA","authority_url":"https://county.gov","result_links":"https://results.enr.clarityelections.com/GA/X/1/ | https://county.gov/results.csv","election_night_candidate":"yes","smallest_observed_unit":"precinct"},
        {"state":"GA","authority_url":"https://other.gov","result_links":"https://county.gov/results.csv","election_night_candidate":"","smallest_observed_unit":"unknown"},
    ]
    got=build_candidates(rows)
    assert len(got)==2
    assert {r["access_family"] for r in got}=={"clarity","tabular_download"}
    assert all(r["ingest_tier"]=="ready_adapter" for r in got)

def test_easy_tier_is_conservative():
    assert ingest_tier("clarity")=="ready_adapter"
    assert ingest_tier("tabular_download", "https://x.gov/results.csv")=="ready_adapter"
    assert ingest_tier("tabular_download", "https://x.gov/results.xlsx")=="needs_adapter_completion"
    assert ingest_tier("scytl")=="needs_adapter_completion"
    assert ingest_tier("electionware")=="needs_adapter_completion"
    assert ingest_tier("pdf")=="document_adapter"
    assert ingest_tier("civicplus")=="discovery_only"
    assert ingest_tier("official_web")=="unsupported_web"
    assert ingest_tier("unknown_web")=="unsupported_web"

def test_summary_reports_exposure_not_fake_unit_coverage():
    rows=[
        {"state":"WA","access_family":"clarity","ingest_tier":"ready_adapter"},
        {"state":"WA","access_family":"clarity","ingest_tier":"ready_adapter"},
        {"state":"MS","access_family":"clarity","ingest_tier":"ready_adapter"},
    ]
    got=summarize(rows,{"WA":39,"MS":82})
    assert got[0]["unique_result_urls"]=="3"
    assert got[0]["state_count"]=="2"
    assert got[0]["expected_units_exposed"]=="121"
