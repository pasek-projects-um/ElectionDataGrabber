from election_data_grabber.readiness_adapter_bridge import readiness_artifact, readiness_route


def test_pipe_delimited_probe_artifacts_feed_structured_selector():
    row={"discovered_artifacts":"https://x.gov/archive.zip|https://x.gov/api/results.json"}
    artifact=readiness_artifact(row)
    assert artifact is not None
    assert artifact.kind=="json"


def test_json_artifact_routes_to_generic_json_runtime():
    family,parser=readiness_route({
        "platform_family":"structured_web",
        "discovered_artifacts":"https://x.gov/api/results.json",
    })
    assert family=="structured_json"
    assert parser=="election_data_grabber.adapters.generic_json:parse_generic_results_json"


def test_csv_artifact_routes_to_generic_csv_runtime():
    family,parser=readiness_route({
        "platform_family":"structured_web",
        "discovered_artifacts":"https://x.gov/results.csv",
    })
    assert family=="tabular_download"
    assert parser=="election_data_grabber.adapters.generic_csv:parse_generic_precinct_csv"


def test_xml_artifact_routes_to_xml_runtime():
    family,parser=readiness_route({
        "platform_family":"structured_web",
        "discovered_artifacts":"https://x.gov/detail.xml",
    })
    assert family=="structured_xml"
    assert parser=="election_data_grabber.adapters.clarity_xml:parse_clarity_like_xml"


def test_excel_artifact_routes_to_generic_excel_runtime():
    family,parser=readiness_route({
        "platform_family":"structured_web",
        "discovered_artifacts":"https://x.gov/results.xlsx",
    })
    assert family=="tabular_download"
    assert parser=="election_data_grabber.adapters.generic_excel:parse_generic_precinct_excel"


def test_scytl_without_probe_artifact_routes_to_vendor_discovery():
    family,parser=readiness_route({"platform_family":"scytl","discovered_artifacts":""})
    assert family=="scytl"
    assert parser=="election_data_grabber.adapters.vendor_structured:discover_vendor_artifacts"


def test_electionware_without_probe_artifact_routes_to_vendor_discovery():
    family,parser=readiness_route({"platform_family":"electionware","discovered_artifacts":""})
    assert family=="electionware"
    assert parser=="election_data_grabber.adapters.vendor_structured:discover_vendor_artifacts"


def test_results_portal_without_probe_artifact_routes_to_structured_discovery():
    family,parser=readiness_route({"platform_family":"results_portal","discovered_artifacts":""})
    assert family=="results_portal"
    assert parser=="election_data_grabber.adapters.vendor_structured:discover_vendor_artifacts"


def test_structured_web_without_probe_artifact_routes_to_structured_discovery():
    family,parser=readiness_route({"platform_family":"structured_web","discovered_artifacts":""})
    assert family=="structured_web"
    assert parser=="election_data_grabber.adapters.vendor_structured:discover_vendor_artifacts"
