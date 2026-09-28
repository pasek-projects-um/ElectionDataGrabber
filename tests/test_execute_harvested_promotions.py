from scripts.execute_harvested_promotions import discover_artifact, parser_for_artifact


def test_parser_for_structured_artifacts():
    assert parser_for_artifact("https://x.gov/results.json")[1].endswith("parse_generic_results_json")
    assert parser_for_artifact("https://x.gov/results.csv")[1].endswith("parse_generic_precinct_csv")
    assert parser_for_artifact("https://x.gov/results.xlsx")[1].endswith("parse_generic_precinct_excel")
    assert parser_for_artifact("https://x.gov/detail.xml")[1].endswith("parse_clarity_like_xml")


def test_vendor_discovery_selects_json_over_zip():
    row={
        "source_url":"https://x.gov/election/",
        "execution_route":"election_data_grabber.adapters.vendor_structured:discover_vendor_artifacts",
    }
    body=b'<a href="archive.zip">Zip</a><script>fetch("/api/results.json")</script>'
    assert discover_artifact(row,body)=="https://x.gov/api/results.json"
