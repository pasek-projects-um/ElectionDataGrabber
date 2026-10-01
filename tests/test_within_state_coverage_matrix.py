from scripts.build_within_state_coverage_matrix import build_matrix


def test_urls_do_not_count_as_enumerated_primary_units():
    first=[{"state":"AA","result_url":"https://aa.gov/results","source_scope":"statewide","election_night_candidate":"true"}]
    den=[{"state":"AA","expected_primary_units":"3","authority_model":"county"}]
    loc=[
        {"state":"AA","jurisdiction_id":"us:aa:county:1"},
        {"state":"AA","jurisdiction_id":"us:aa:county:2"},
    ]
    leads=[
        {"state":"AA","jurisdiction_id":"us:aa:county:1","lead_url":"https://aa.gov/a"},
        {"state":"AA","jurisdiction_id":"us:aa:county:1","lead_url":"https://aa.gov/b"},
        {"state":"AA","jurisdiction_id":"us:aa:county:2","lead_url":"https://aa.gov/c"},
    ]
    rows=build_matrix(first,den,loc,leads,[])
    row=rows[0]
    assert row["expected_primary_units"]=="3"
    assert row["enumerated_primary_units"]=="2"
    assert row["units_with_any_lead"]=="2"
    assert row["catalogued_source_leads"]=="3"
    assert row["enumeration_ratio"]=="0.6667"
    assert row["lead_coverage_ratio"]=="1.0000"
    assert "enumeration_gap" in row["depth_reasons"]


def test_execution_stages_are_counted_separately():
    first=[{"state":"AA","result_url":"https://aa.gov/results","source_scope":"statewide","election_night_candidate":"true"}]
    den=[{"state":"AA","expected_primary_units":"1","authority_model":"state"}]
    loc=[{"state":"AA","jurisdiction_id":"us:aa:state:aa"}]
    leads=[{"state":"AA","jurisdiction_id":"us:aa:state:aa","lead_url":"https://aa.gov/results"}]
    execution=[
        {"state":"AA","stage":"parser_selected"},
        {"state":"AA","stage":"normalized"},
        {"state":"AA","stage":"replay_tested"},
        {"state":"AA","stage":"refresh_verified"},
    ]
    row=build_matrix(first,den,loc,leads,execution)[0]
    assert row["executable_sources"]=="4"
    assert row["normalized_sources"]=="3"
    assert row["replay_tested_sources"]=="2"
    assert row["refresh_verified_sources"]=="1"
    assert row["highest_execution_stage"]=="refresh_verified"
