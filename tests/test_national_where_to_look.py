from pathlib import Path
from scripts.build_national_where_to_look import build


def test_compiler_keeps_multiple_page_roles_and_exposes_gaps(tmp_path: Path):
    (tmp_path/"us_primary_election_localities.csv").write_text(
        "jurisdiction_id,state,jurisdiction_level,canonical_name,final_evidence_url,election_night_evidence_url,assessment_status\n"
        "us:mi:county:alpha,MI,county,Alpha,https://alpha.example/history,https://alpha.example/live,verified\n"
        "us:mi:county:beta,MI,county,Beta,,,pending\n")
    (tmp_path/"us_state_central_authority_sources.csv").write_text(
        "state,central_authority_url,status\nMI,https://state.example/elections,candidate\n")
    for name,header in (
        ("mi_county_authorities.csv","county,authority_url"),
        ("oh_county_authorities.csv","county,authority_url"),
        ("me_locality_authorities.csv","locality,county,authority_url"),
        ("sources.csv","source_id,jurisdiction,state,url,official"),
        ("us_local_reporting_sources.csv","state,locality_type,locality_name,authority_url,results_url,status"),
    ):
        (tmp_path/name).write_text(header+"\n")
    rows,gaps,summary=build(tmp_path)
    assert summary["candidate_pages"]==4
    assert summary["localities_without_registered_url"]==1
    assert gaps[0]["jurisdiction_id"]=="us:mi:county:beta"\n    assert gaps[0]["gap"]=="state_fallback_only"\n    assert summary["localities_without_any_start"]==0\n    assert any(row["jurisdiction_id"]=="us:mi:county:beta" and row["verification_status"]=="fallback_unverified_for_locality" for row in rows)
    assert {row["page_role"] for row in rows}=={
        "historical_or_final_results","election_night_lead","state_election_authority","state_directory_fallback"}
