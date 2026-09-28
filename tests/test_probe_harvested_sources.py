from scripts.probe_harvested_sources import probe


def test_probe_preserves_failed_fetch_as_explicit_status(monkeypatch):
    monkeypatch.setattr(
        "scripts.probe_harvested_sources.fetch_text",
        lambda url,timeout:(None,"http_403","403"),
    )
    rows=probe([{"state":"AA","source_url":"https://aa.gov/results","source_origin":"internal","platform_family":"official_web"}])
    assert rows[0]["fetch_status"]=="http_403"
    assert rows[0]["http_status"]=="403"


def test_probe_fingerprints_fetchable_source(monkeypatch):
    monkeypatch.setattr(
        "scripts.probe_harvested_sources.fetch_text",
        lambda url,timeout:("<html>Election Night Reporting</html>","fetchable","200"),
    )
    rows=probe([{"state":"AA","source_url":"https://aa.gov/results","source_origin":"internal","platform_family":"official_web"}])
    assert rows[0]["fetch_status"]=="fetchable"
    assert rows[0]["platform_family"]=="clarity"
