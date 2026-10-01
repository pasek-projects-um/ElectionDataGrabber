from scripts.build_harvested_execution_promotions import promotion_action


def test_json_artifact_promotes_to_executable_parser():
    family,route,action=promotion_action({
        "fetch_status":"fetchable",
        "platform_family":"structured_web",
        "discovered_artifacts":"https://x.gov/api/results.json",
    })
    assert family=="structured_json"
    assert route=="election_data_grabber.adapters.generic_json:parse_generic_results_json"
    assert action=="execute_now"


def test_results_portal_without_artifact_uses_discovery_not_new_adapter():
    family,route,action=promotion_action({
        "fetch_status":"fetchable",
        "platform_family":"results_portal",
        "discovered_artifacts":"",
    })
    assert family=="results_portal"
    assert route=="election_data_grabber.adapters.vendor_structured:discover_vendor_artifacts"
    assert action=="discover_artifact"


def test_nonfetchable_source_is_blocked_before_routing():
    _,route,action=promotion_action({
        "fetch_status":"http_403",
        "platform_family":"clarity",
        "discovered_artifacts":"",
    })
    assert route==""
    assert action=="fetch_blocked"
