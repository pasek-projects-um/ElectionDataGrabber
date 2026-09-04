from election_data_grabber.discovery import fingerprint_platform


def test_clarity_fingerprint():
    assert (
        fingerprint_platform("https://results.enr.clarityelections.com/MI/example")
        == "clarity"
    )


def test_washtenaw_live_fingerprint():
    assert (
        fingerprint_platform(
            "https://electionresults.ewashtenaw.org/electionreporting/aug2026/index.jsp"
        )
        == "washtenaw_enr"
    )
