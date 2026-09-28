from scripts.build_geography_source_ledger import build_geography_ledger, build_source_leads, unresolved_queue

def test_geography_search_queue_preserves_unresolved_units():
    rows=[
        {"jurisdiction_id":"us:aa:county:a","authority_id":"us:authority:a","state":"AA","jurisdiction_level":"county","canonical_name":"Alpha","coverage_status":"both","final_evidence_url":"https://aa.gov/a","election_night_evidence_url":"https://aa.gov/live"},
        {"jurisdiction_id":"us:aa:city:b","authority_id":"us:authority:b","state":"AA","jurisdiction_level":"city","canonical_name":"Beta","coverage_status":"enumerated_unresolved","final_evidence_url":"","election_night_evidence_url":""},
    ]
    ledger=build_geography_ledger(rows)
    queue=unresolved_queue(ledger)
    assert len(ledger)==2
    assert [r["canonical_name"] for r in queue]==["Beta"]
    assert queue[0]["search_query"]=="Beta AA election results"


def test_multiple_outlets_for_same_geography_are_preserved():
    rows=[{
        "jurisdiction_id":"us:aa:county:alpha","authority_id":"us:authority:alpha","state":"AA",
        "jurisdiction_level":"county","canonical_name":"Alpha","coverage_status":"both",
        "final_evidence_url":"https://aa.gov/final","election_night_evidence_url":"https://aa.gov/live",
    }]
    leads=build_source_leads(rows)
    assert len(leads)==2
    assert {r["source_role"] for r in leads}=={"final","election_night"}
    assert {r["lead_url"] for r in leads}=={"https://aa.gov/final","https://aa.gov/live"}
