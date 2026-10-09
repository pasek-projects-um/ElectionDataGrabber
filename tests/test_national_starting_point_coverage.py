from pathlib import Path
from scripts.audit_national_starting_point_coverage import audit


def test_missing_named_jurisdictions_prevent_100_percent(tmp_path: Path):
    files = {
        "us_primary_election_localities.csv":
            "jurisdiction_id,state,jurisdiction_level,canonical_name,final_evidence_url,election_night_evidence_url\n"
            "us:mi:county:alpha,MI,county,Alpha,https://example.org/results,\n",
        "us_primary_election_locality_denominators.csv":
            "state,expected_primary_units,estimate_status\nMI,2,high_confidence\n",
        "us_state_central_authority_sources.csv":
            "state,central_authority_url\nMI,https://state.example/elections\n",
        "mi_county_authorities.csv": "county,authority_url\n",
        "oh_county_authorities.csv": "county,authority_url\n",
        "me_locality_authorities.csv": "locality,county,authority_url\n",
        "sources.csv": "source_id,jurisdiction,state,url,official\n",
        "us_local_reporting_sources.csv":
            "state,locality_type,locality_name,authority_url,results_url,status\n",
    }
    for name, content in files.items():
        (tmp_path / name).write_text(content)
    states, summary = audit(tmp_path)
    assert states[0]["unnamed_units"] == 1
    assert summary["units_with_any_start"] == 1
    assert not summary["national_100_percent"]


def test_provisional_denominator_cannot_claim_complete(tmp_path: Path):
    files = {
        "us_primary_election_localities.csv":
            "jurisdiction_id,state,jurisdiction_level,canonical_name,final_evidence_url,election_night_evidence_url\n"
            "us:mi:county:alpha,MI,county,Alpha,,\n",
        "us_primary_election_locality_denominators.csv":
            "state,expected_primary_units,estimate_status\nMI,1,provisional\n",
        "us_state_central_authority_sources.csv":
            "state,central_authority_url\nMI,https://state.example/elections\n",
        "mi_county_authorities.csv": "county,authority_url\n",
        "oh_county_authorities.csv": "county,authority_url\n",
        "me_locality_authorities.csv": "locality,county,authority_url\n",
        "sources.csv": "source_id,jurisdiction,state,url,official\n",
        "us_local_reporting_sources.csv":
            "state,locality_type,locality_name,authority_url,results_url,status\n",
    }
    for name, content in files.items():
        (tmp_path / name).write_text(content)
    _, summary = audit(tmp_path)
    assert summary["units_with_any_start"] == 1
    assert summary["provisional_state_count"] == 1
    assert not summary["national_100_percent"]
