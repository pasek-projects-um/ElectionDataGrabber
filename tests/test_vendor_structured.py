from election_data_grabber.adapters.vendor_structured import (
    discover_vendor_artifacts,
    is_electionware,
    is_scytl,
)


def test_scytl_and_electionware_signatures():
    assert is_scytl("https://results.example/",b"<meta content='Scytl'>")
    assert is_electionware("https://results.example/",b"Electionware")


def test_vendor_artifacts_find_relative_api_and_downloads():
    urls=discover_vendor_artifacts(
        b'<script>fetch("/api/results.json")</script><a href="precinct.csv">Download</a>',
        "https://x.gov/election/",
    )
    assert "https://x.gov/api/results.json" in urls
    assert "https://x.gov/election/precinct.csv" in urls
