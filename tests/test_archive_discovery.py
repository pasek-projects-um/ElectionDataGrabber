from election_data_grabber.adapters.archive_discovery import discover_election_artifacts


def test_discovers_mixed_municipal_election_artifacts():
    html=b'''
    <a href="/files/2024-general-results.pdf">2024 General Election Results</a>
    <a href="/files/ward-turnout.xlsx">Ward Turnout</a>
    <a href="/parks">Parks</a>
    '''
    rows=discover_election_artifacts(html,"https://example.test/elections/")
    assert [(r.kind,r.label) for r in rows] == [
        ("pdf","2024 General Election Results"),
        ("spreadsheet","Ward Turnout"),
    ]
