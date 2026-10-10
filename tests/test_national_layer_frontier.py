import csv

from scripts.build_national_layer_frontier import compile_frontier


def registry(root, direct=False):
    local_url = "https://county.gov/results" if direct else ""
    files = {
        "us_primary_election_localities.csv":
            "jurisdiction_id,state,jurisdiction_level,canonical_name,final_evidence_url\n"
            f"us:mi:county:alpha,MI,county,Alpha,{local_url}\n"
            f"us:mi:county:beta,MI,county,Beta,{local_url}\n",
        "us_primary_election_locality_denominators.csv":
            "state,expected_primary_units,estimate_status\nMI,2,provisional\n",
        "us_state_central_authority_sources.csv":
            "state,central_authority_url\nMI,https://state.gov/directory\n",
        "mi_county_authorities.csv": "county,authority_url\n",
        "oh_county_authorities.csv": "county,authority_url\n",
        "me_locality_authorities.csv": "locality,county,authority_url\n",
        "sources.csv": "source_id,jurisdiction,state,url,official\n",
        "us_local_reporting_sources.csv":
            "state,locality_type,locality_name,authority_url,results_url,status\n",
    }
    for name, body in files.items():
        (root / name).write_text(body)


def catalog(root, parent, status="not_fetched", kind="dashboard_candidate"):
    row = {
        "source_id": "observed", "url": "https://vendor.gov/results",
        "states": "MI", "catalog_kind": kind, "platform_families": "clarity",
        "target_status": status, "observed_from": parent,
    }
    with (root / "discovered_result_sources.csv").open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(row))
        writer.writeheader()
        writer.writerow(row)


def test_shared_state_directory_is_one_task_not_local_result_coverage(tmp_path):
    registry(tmp_path)
    catalog(tmp_path, "https://state.gov/directory")
    units, starts, sources, states, summary = compile_frontier(tmp_path)
    assert len(starts) == 1
    assert starts[0]["observed_child_leads"] == 1
    assert starts[0]["unpublished_feed_status"] == "unresolved_not_missing"
    assert "iframe_targets" in starts[0]["watch_signals"]
    assert all(u["observed_child_lead_urls"] == "" for u in units)
    assert all(u["next_action"] == "resolve_local_authority_from_state_directory" for u in units)
    assert states[0]["units_using_state_fallback_only"] == 2
    assert states[0]["enumeration_review_required"]
    assert sources[0]["served_jurisdiction_verified"] == "false"
    assert not summary["starting_point_audit"]["national_100_percent"]


def test_exact_local_provenance_retains_all_associations_without_promoting_service(tmp_path):
    registry(tmp_path, direct=True)
    catalog(tmp_path, "https://county.gov/results#section")
    units, starts, _, states, _ = compile_frontier(tmp_path)
    local_tasks = [t for t in starts if t["url"] == "https://county.gov/results"]
    assert len(local_tasks) == 1
    assert len(local_tasks[0]["associated_unit_ids"].split(" | ")) == 2
    assert all(u["next_action"] == "inspect_observed_result_leads" for u in units)
    assert all(u["served_jurisdiction_verified"] == "false" for u in units)
    assert states[0]["units_with_observed_child_leads"] == 2


def test_same_host_does_not_imply_same_locality_or_provenance(tmp_path):
    registry(tmp_path, direct=True)
    catalog(tmp_path, "https://county.gov/another-office")
    units, _, _, _, _ = compile_frontier(tmp_path)
    assert all(u["next_action"] == "extract_links_from_local_start" for u in units)


def test_fetch_failure_is_investigation_not_missing_source(tmp_path):
    registry(tmp_path)
    catalog(tmp_path, "https://state.gov/directory", "fetch_failed", "result_artifact_lead")
    _, _, sources, _, summary = compile_frontier(tmp_path)
    assert sources[0]["next_action"] == "investigate_fetch_failure"
    assert summary["source_next_actions"] == {"investigate_fetch_failure": 1}
