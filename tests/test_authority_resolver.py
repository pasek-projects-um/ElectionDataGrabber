from election_data_grabber.authority_resolver import discover_candidate_links

def test_authority_resolver_prefers_election_links():
    html='''<a href="/parks">Parks</a><a href="/town-clerk/elections">Elections</a><a href="/elections/results/2024.pdf">2024 results</a>'''
    got=discover_candidate_links("https://example.gov/",html)
    urls=[x.url for x in got]
    assert "https://example.gov/elections/results/2024.pdf" in urls
    assert "https://example.gov/town-clerk/elections" in urls
    assert "https://example.gov/parks" not in urls
