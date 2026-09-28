from scripts.build_external_lead_verification_queue import build_verification_queue


def test_queue_prioritizes_legacy_and_cycle_specific_unverified_leads():
    rows=[
        {"state":"AA","source_role":"early_vote","lead_url":"https://aa.gov/data","origin_repository":"r","origin_locator":"x","official_status":"likely_official","verification_status":"unverified","notes":""},
        {"state":"BB","source_role":"early_vote","lead_url":"http://bb.gov/2020?id=1","origin_repository":"r","origin_locator":"y","official_status":"likely_official","verification_status":"unverified","notes":""},
    ]
    queue=build_verification_queue(rows)
    assert queue[0]["state"]=="BB"
    assert "legacy_http" in queue[0]["verification_reasons"]
    assert "cycle_or_current_pointer" in queue[0]["verification_reasons"]


def test_verified_lead_has_lower_priority():
    rows=[
        {"state":"AA","source_role":"early_vote","lead_url":"https://aa.gov/data","origin_repository":"r","origin_locator":"x","official_status":"likely_official","verification_status":"verified","notes":""},
        {"state":"BB","source_role":"early_vote","lead_url":"https://bb.gov/data","origin_repository":"r","origin_locator":"y","official_status":"likely_official","verification_status":"unverified","notes":""},
    ]
    queue=build_verification_queue(rows)
    assert queue[0]["state"]=="BB"
