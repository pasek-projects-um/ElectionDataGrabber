import csv
from pathlib import Path

from scripts.audit_national_promotion_gaps import (
    build_near_ready,
    build_web_host_summary,
)


def test_near_ready_identifies_excel_blockers():
    rows = [
        {
            "state": "DC",
            "result_url": "https://example.test/a.xls",
            "result_host": "example.test",
            "access_family": "tabular_download",
            "ingest_tier": "needs_adapter_completion",
            "election_night_candidate": "false",
            "smallest_observed_unit": "precinct",
        },
        {
            "state": "ME",
            "result_url": "https://example.test/b.xlsx",
            "result_host": "example.test",
            "access_family": "tabular_download",
            "ingest_tier": "needs_adapter_completion",
            "election_night_candidate": "false",
            "smallest_observed_unit": "unknown",
        },
    ]
    out = build_near_ready(rows)
    assert [r["promotion_blocker"] for r in out] == [
        "xls_parser_required",
        "xlsx_parser_required",
    ]


def test_web_hosts_prioritize_election_night_and_volume():
    rows = [
        {
            "state": "AA",
            "result_url": "https://results.example/a",
            "result_host": "results.example",
            "access_family": "official_web",
            "ingest_tier": "unsupported_web",
            "election_night_candidate": "true",
        },
        {
            "state": "BB",
            "result_url": "https://results.example/b",
            "result_host": "results.example",
            "access_family": "official_web",
            "ingest_tier": "unsupported_web",
            "election_night_candidate": "false",
        },
        {
            "state": "CC",
            "result_url": "https://archive.example/c",
            "result_host": "archive.example",
            "access_family": "official_web",
            "ingest_tier": "unsupported_web",
            "election_night_candidate": "false",
        },
    ]
    out = build_web_host_summary(rows)
    assert out[0]["result_host"] == "results.example"
    assert out[0]["candidate_count"] == "2"
    assert out[0]["election_night_candidate_count"] == "1"
