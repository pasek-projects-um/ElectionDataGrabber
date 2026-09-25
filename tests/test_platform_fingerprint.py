from election_data_grabber.platform_fingerprint import fingerprint_result_surface


def test_detects_clarity_signature_and_download():
    result = fingerprint_result_surface(
        "https://county.gov/results/",
        '<title>Election Night Reporting</title><a href="detail.xml">XML</a>',
    )
    assert result.family == "clarity"
    assert result.confidence == "high"
    assert result.discovered_artifacts == ("https://county.gov/results/detail.xml",)


def test_detects_structured_unknown_web():
    result = fingerprint_result_surface(
        "https://results.example/election",
        '<script>fetch("/api/results.json")</script>',
    )
    assert result.family == "structured_web"
    assert result.confidence == "medium"
    assert "https://results.example/api/results.json" in result.discovered_artifacts


def test_unknown_plain_page_stays_low_confidence():
    result = fingerprint_result_surface("https://example.com/results", "<html>Results</html>")
    assert result.family == "unknown_web"
    assert result.confidence == "low"
