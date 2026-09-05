from election_data_grabber.washtenaw_ingest import parse_summary


def test_parse_summary_discovers_precinct_pages_and_counts():
    html = b"""
    <html><body>
      <div>This report created: Wednesday, Aug 12, 2026 11:15:16 AM</div>
      <div>Total Precincts: 112</div>
      <div>Fully Counted Precincts: 110</div>
      <div>Partially Counted Precincts: 2</div>
      <div>Registered Voters: 300,000</div>
      <div>Ballots Cast: 120,000</div>
      <a href="precinctreport1.html">Precinct 1</a>
      <a href="precinctreport2.html">Precinct 2</a>
      <a href="precinctreport2.html">Precinct 2 duplicate</a>
    </body></html>
    """

    summary = parse_summary(
        html,
        "https://electionresults.ewashtenaw.org/electionreporting/aug2026/index.jsp",
    )

    assert summary.precincts_total == 112
    assert summary.precincts_counted == 110
    assert summary.precincts_partially_counted == 2
    assert summary.registered_voters == 300000
    assert summary.ballots_cast == 120000
    assert len(summary.precinct_urls) == 2
    assert summary.precinct_urls[0].endswith("precinctreport1.html")
    assert summary.precinct_urls[1].endswith("precinctreport2.html")
