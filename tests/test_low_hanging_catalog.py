from election_data_grabber.easy_ingest import ingest_tier
from election_data_grabber.supported_ingest import supported_ingest_manifest


def test_excel_downloads_are_catalogued_as_ready():
    assert ingest_tier("tabular_download", "https://example.gov/results.xls") == "ready_adapter"
    assert ingest_tier("tabular_download", "https://example.gov/results.xlsx?download=1") == "ready_adapter"


def test_excel_manifest_selects_excel_adapter():
    rows = [{
        "state": "ME",
        "result_url": "https://example.gov/results.xlsx",
        "access_family": "tabular_download",
        "ingest_tier": "ready_adapter",
        "smallest_observed_unit": "unknown",
    }]
    manifest = supported_ingest_manifest(rows)
    assert len(manifest) == 1
    assert manifest[0]["parser"] == "election_data_grabber.adapters.generic_excel:parse_generic_precinct_excel"
