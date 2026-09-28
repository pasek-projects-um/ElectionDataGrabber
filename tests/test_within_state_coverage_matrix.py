from scripts.build_within_state_coverage_matrix import build_matrix

def test_matrix_keeps_catalog_and_execution_separate():
    first=[{"state":"AA","result_url":"https://aa.gov/results","source_scope":"statewide","election_night_candidate":"true","smallest_observed_unit":"county"}]
    candidates=[{"state":"AA","result_host":"aa.gov"},{"state":"AA","result_host":"county.aa.gov"}]
    execution=[{"state":"AA","stage":"replay_tested"}]
    rows=build_matrix(first,candidates,execution)
    assert rows[0]["catalogued_result_urls"]=="2"
    assert rows[0]["catalogued_hosts"]=="2"
    assert rows[0]["highest_execution_stage"]=="replay_tested"
    assert rows[0]["normalized_sources"]=="1"
