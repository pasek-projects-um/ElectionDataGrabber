from scripts.classify_harvested_execution_residuals import residual_class, summarize


def test_residual_classification():
    assert residual_class({"execution_stage":"replay_tested","failure_class":"","access_family":"clarity"})=="complete"
    assert residual_class({"execution_stage":"discovered","failure_class":"http_403","access_family":"official_web"})=="fetch_hardening"
    assert residual_class({"execution_stage":"discovered","failure_class":"no_structured_artifact_discovered","access_family":"results_portal"})=="artifact_discovery"
    assert residual_class({"execution_stage":"parser_selected","failure_class":"invalid_json_payload","access_family":"structured_json"})=="schema_adaptation"
    assert residual_class({"execution_stage":"parser_selected","failure_class":"parser_not_executable","access_family":"foo"})=="new_platform_or_parser"


def test_summary_prioritizes_known_execution_followups():
    rows=[
        {"execution_stage":"parser_selected","failure_class":"","access_family":"clarity"},
        {"execution_stage":"discovered","failure_class":"http_403","access_family":"official_web"},
    ]
    out=summarize(rows)
    assert out[0]["priority"] >= out[1]["priority"]
