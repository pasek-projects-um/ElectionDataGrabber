from datetime import datetime, timezone
from pathlib import Path

from election_data_grabber.adapters.clarity_xml import parse_clarity_like_xml
from election_data_grabber.adapters.generic_csv import parse_generic_precinct_csv
from election_data_grabber.adapters.washtenaw_html import parse_washtenaw_like_html

NOW = datetime(2026, 11, 3, tzinfo=timezone.utc)


def _assert_common_contract(rows):
    assert rows
    assert all(r.reporting_unit_id for r in rows)
    assert all(r.reporting_unit_name for r in rows)
    assert all(r.contest_name for r in rows)
    assert all(r.choice_name for r in rows)
    assert all(r.votes >= 0 for r in rows)
    assert all(r.raw_vote_mode for r in rows)


def test_fixture_adapters_meet_common_contract():
    csv_rows = parse_generic_precinct_csv(
        Path("tests/fixtures/generic_precinct_modes.csv").read_bytes(),
        election_id="fixture",
        jurisdiction_id="fixture-csv",
        source_id="csv",
        fetched_at=NOW,
    )
    xml_rows = parse_clarity_like_xml(
        Path("tests/fixtures/clarity_like.xml").read_bytes(),
        election_id="fixture",
        jurisdiction_id="fixture-xml",
        source_id="xml",
        fetched_at=NOW,
    )
    html_rows = parse_washtenaw_like_html(
        Path("tests/fixtures/washtenaw_like.html").read_bytes(),
        election_id="fixture",
        jurisdiction_id="fixture-html",
        source_id="html",
        fetched_at=NOW,
    )

    for rows in (csv_rows, xml_rows, html_rows):
        _assert_common_contract(rows)
