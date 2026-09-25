import scripts.probe_ranked_platforms as mod


def test_probe_prioritizes_election_night_then_volume(monkeypatch):
    rows = [
        {"result_host":"bulk.example","sample_url":"https://bulk.example","candidate_count":"20","election_night_candidate_count":"0"},
        {"result_host":"live.example","sample_url":"https://live.example","candidate_count":"2","election_night_candidate_count":"2"},
    ]
    monkeypatch.setattr(mod, "fetch_text", lambda url, timeout: ("<html>Election Night Reporting</html>", ""))
    out = mod.probe(rows, timeout=1)
    assert out[0]["result_host"] == "live.example"
    assert out[0]["family"] == "clarity"
    assert out[0]["confidence"] == "high"


def test_probe_records_fetch_failure(monkeypatch):
    rows = [
        {"result_host":"x.example","sample_url":"https://x.example","candidate_count":"1","election_night_candidate_count":"1"},
    ]
    monkeypatch.setattr(mod, "fetch_text", lambda url, timeout: (None, "timeout"))
    out = mod.probe(rows, timeout=1)
    assert out[0]["fetch_failure"] == "timeout"
    assert out[0]["family"] == ""
