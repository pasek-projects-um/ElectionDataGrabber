from election_data_grabber.state_directory_profiles import structured_candidates, alaska_state_result_candidates

def test_structured_candidates_uses_row_context_and_data_urls():
    html=b'''<table><tr><td>Example County</td><td><a href="https://example.gov/elections">Office</a></td></tr></table>
    <div data-website="/county/clerk"></div>'''
    got=structured_candidates("NM",html,"https://sos.example.gov/directory")
    assert "https://example.gov/elections" in got
    assert "https://sos.example.gov/county/clerk" in got

def test_alaska_discovers_state_result_products():
    html=b'<a href="/elections/results/2024-general">2024 General Election Results</a>'
    assert alaska_state_result_candidates(html,"https://www.elections.alaska.gov/")==[
      "https://www.elections.alaska.gov/elections/results/2024-general"
    ]
