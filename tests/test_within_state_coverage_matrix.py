from scripts.build_within_state_coverage_matrix import build_matrix, build_priority_queue

def test_matrix_keeps_catalog_and_execution_separate():
    first=[{"state":"AA","result_url":"https://aa.gov/results","source_scope":"statewide","election_night_candidate":"true","smallest_observed_unit":"county"}]
    candidates=[{"state":"AA","result_host":"aa.gov","result_url":"https://aa.gov/a"},{"state":"AA","result_host":"county.aa.gov","result_url":"https://county.aa.gov/b"}]
    execution=[{"state":"AA","stage":"replay_tested"}]
    profiles=[{"state":"AA","profile_type":"county_directory","expected_units":"4"}]
    rows=build_matrix(first,candidates,execution,profiles)
    row=rows[0]
    assert row["catalogued_result_urls"]=="2"
    assert row["catalogued_hosts"]=="2"
    assert row["expected_units"]=="4"
    assert row["observed_catalog_units"]=="2"
    assert row["catalog_depth_ratio"]=="0.5000"
    assert row["highest_execution_stage"]=="replay_tested"
    assert row["normalized_sources"]=="1"
    assert "jurisdiction_gap" in row["depth_reasons"]
    assert "election_night_refresh_unverified" in row["depth_reasons"]

def test_priority_queue_favors_election_night_and_uncovered_depth():
    first=[
        {"state":"AA","result_url":"https://aa.gov/results","source_scope":"statewide","election_night_candidate":"false","smallest_observed_unit":"county"},
        {"state":"BB","result_url":"https://bb.gov/results","source_scope":"county","election_night_candidate":"true","smallest_observed_unit":"precinct"},
    ]
    rows=build_matrix(first,[],[],[])
    queue=build_priority_queue(rows)
    assert queue[0]["state"]=="BB"
    assert int(queue[0]["depth_priority"]) > int(queue[1]["depth_priority"])
