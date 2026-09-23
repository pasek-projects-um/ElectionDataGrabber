from election_data_grabber.supported_ingest import supported_ingest_manifest

def test_manifest_contains_only_real_current_adapter_paths():
    rows=[
        {"state":"WV","result_url":"https://results.enr.clarityelections.com/WV/1","access_family":"clarity","ingest_tier":"ready_adapter","smallest_observed_unit":"precinct"},
        {"state":"DC","result_url":"https://x.gov/results.xls","access_family":"tabular_download","ingest_tier":"needs_adapter_completion","smallest_observed_unit":"precinct"},
        {"state":"GA","result_url":"https://x.gov/results","access_family":"scytl","ingest_tier":"needs_adapter_completion","smallest_observed_unit":"unknown"},
    ]
    got=supported_ingest_manifest(rows)
    assert len(got)==1
    assert got[0]["state"]=="WV"
    assert got[0]["parser"].endswith(":discover_clarity_downloads")
    assert got[0]["status"]=="supported_unverified"
