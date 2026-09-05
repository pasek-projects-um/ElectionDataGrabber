from election_data_grabber.washtenaw_ingest import parse_summary


SUMMARY_2024 = b"""
<html><body>
<div>Total Precincts: 120 Fully Counted Precincts: 120 Partially Counted Precincts: 0</div>
<a href="precinctreport1.html">City of Ann Arbor, Ward 1, Precinct 1</a>
<a href="precinctreport2.html">City of Ann Arbor, Ward 1, Precinct 2</a>
</body></html>
"""

SUMMARY_2025 = b"""
<html><body>
<a href="precinctreport1.html">Ann Arbor City, Ward 1 P1 & Ward 4 P31</a>
<a href="precinctreport2.html">Ann Arbor City, Ward 1, Precinct 2</a>
<a href="precinctreport3.html">Ann Arbor City, Ward 1, Precinct 5 & 6</a>
</body></html>
"""


def test_2024_precinct_enumeration():
    summary = parse_summary(SUMMARY_2024, "https://example.test/election/")
    assert summary.precincts_total == 120
    assert len(summary.precinct_urls) == 2
    assert summary.precinct_urls[0].endswith("precinctreport1.html")


def test_2025_consolidated_reporting_units_are_preserved():
    summary = parse_summary(SUMMARY_2025, "https://example.test/election/")
    assert len(summary.precinct_urls) == 3
    # Consolidated units must not be split or silently coerced into a single precinct.
    assert any(url.endswith("precinctreport1.html") for url in summary.precinct_urls)
    assert any(url.endswith("precinctreport3.html") for url in summary.precinct_urls)
