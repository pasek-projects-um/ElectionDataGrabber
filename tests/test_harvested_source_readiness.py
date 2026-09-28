from scripts.summarize_harvested_source_readiness import next_action


def test_fetch_failure_is_blocked():
    assert next_action({"fetch_status":"http_403","platform_family":"","discovered_artifacts":""})=="fetch_blocked"


def test_clarity_is_existing_adapter():
    assert next_action({"fetch_status":"fetchable","platform_family":"clarity","discovered_artifacts":""})=="execute_existing_adapter"


def test_structured_artifacts_precede_new_adapter_work():
    assert next_action({"fetch_status":"fetchable","platform_family":"unknown_web","discovered_artifacts":"https://x.gov/results.csv"})=="artifact_discovery"


def test_unknown_fetchable_web_requires_followup():
    assert next_action({"fetch_status":"fetchable","platform_family":"unknown_web","discovered_artifacts":""})=="platform_probe_followup"
