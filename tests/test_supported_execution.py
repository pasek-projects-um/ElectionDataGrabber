from datetime import datetime, timezone

from election_data_grabber.execution_maturity import ExecutionStage, maturity_row
from election_data_grabber.supported_execution import execute_supported_body

NOW = datetime(2026, 11, 3, tzinfo=timezone.utc)


def test_direct_csv_executes_to_replay_tested_evidence():
    manifest = {
        "state": "MI",
        "result_url": "https://example.gov/results.csv",
        "access_family": "tabular_download",
        "parser": "election_data_grabber.adapters.generic_csv:parse_generic_precinct_csv",
        "smallest_observed_unit": "precinct",
    }
    body = (
        "precinct,office,candidate,election_day,absentee\n"
        "Ward 1,Mayor,Alice,100,40\n"
        "Ward 1,Mayor,Bob,90,35\n"
    ).encode()
    evidence = execute_supported_body(
        manifest,
        body,
        election_id="2026-general",
        jurisdiction_id="us:mi:test",
        source_id="fixture-csv",
        fetched_at=NOW,
    )
    assert evidence.stage == ExecutionStage.REPLAY_TESTED
    assert evidence.observation_count == 4
    assert evidence.vote_modes_preserved is True
    assert len(evidence.snapshot_sha256) == 64
    assert maturity_row(evidence)["execution_stage"] == "replay_tested"


def test_enhanced_voting_executes_embedded_json():
    manifest = {
        "state": "GA",
        "result_url": "https://app.enhancedvoting.com/results/public/x/elections/y",
        "access_family": "enhanced_voting",
        "parser": "election_data_grabber.adapters.enhanced_voting:parse_enhanced_voting_html",
        "smallest_observed_unit": "precinct",
    }
    body = b'''<script id="__NEXT_DATA__" type="application/json">{"props":{"pageProps":{"results":[{"precinctName":"P1","contestName":"Mayor","candidateName":"Alice","total":12}]}}}</script>'''
    evidence = execute_supported_body(
        manifest,
        body,
        election_id="2026-general",
        jurisdiction_id="us:ga:test",
        source_id="fixture-enhanced",
        fetched_at=NOW,
    )
    assert evidence.stage == ExecutionStage.REPLAY_TESTED
    assert evidence.observation_count == 1
    assert evidence.vote_modes_preserved is False


def test_successful_parser_with_no_rows_stays_below_normalized():
    manifest = {
        "state": "MI",
        "result_url": "https://example.gov/results.csv",
        "access_family": "tabular_download",
        "parser": "election_data_grabber.adapters.generic_csv:parse_generic_precinct_csv",
        "smallest_observed_unit": "precinct",
    }
    evidence = execute_supported_body(
        manifest,
        b"precinct,office,candidate,total\n",
        election_id="2026-general",
        jurisdiction_id="us:mi:test",
        source_id="empty-csv",
        fetched_at=NOW,
    )
    assert evidence.stage == ExecutionStage.PARSE_EXECUTED
    assert evidence.failure_class == "no_normalized_observations"


def test_clarity_landing_page_is_not_promoted_to_normalized():
    manifest = {
        "state": "WV",
        "result_url": "https://results.enr.clarityelections.com/WV/X/1/",
        "access_family": "clarity",
        "parser": "election_data_grabber.adapters.clarity:discover_clarity_downloads",
        "smallest_observed_unit": "precinct",
    }
    evidence = execute_supported_body(
        manifest,
        b'<a href="detail.xml">Precinct Detail</a>',
        election_id="2026-general",
        jurisdiction_id="us:wv:test",
        source_id="clarity-page",
        fetched_at=NOW,
    )
    assert evidence.stage == ExecutionStage.FETCHABLE
    assert evidence.failure_class == "requires_download_artifact_selection"
