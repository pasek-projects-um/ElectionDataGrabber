from scripts.summarize_harvested_execution_depth import summarize


def test_summary_keeps_maturity_levels_distinct():
    rows=[
        {"state":"AA","execution_stage":"parser_selected","failure_class":"artifact_discovered_requires_fetch"},
        {"state":"AA","execution_stage":"normalized","failure_class":""},
        {"state":"AA","execution_stage":"replay_tested","failure_class":""},
        {"state":"BB","execution_stage":"discovered","failure_class":"http_403"},
    ]
    out={r["state"]:r for r in summarize(rows)}
    assert out["AA"]["sources_attempted"]=="3"
    assert out["AA"]["normalized_or_higher"]=="2"
    assert out["AA"]["replay_tested_or_higher"]=="1"
    assert out["AA"]["refresh_verified"]=="0"
    assert out["AA"]["highest_execution_stage"]=="replay_tested"
    assert out["BB"]["fetch_or_execution_failures"]=="1"
