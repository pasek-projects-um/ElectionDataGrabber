from datetime import datetime, timezone
from pathlib import Path

from election_data_grabber.adapters.washtenaw_html import parse_washtenaw_like_html
from election_data_grabber.models import VoteMode


def test_washtenaw_like_html_preserves_order_modes_and_unit():
    rows = parse_washtenaw_like_html(
        Path("tests/fixtures/washtenaw_like.html").read_bytes(),
        election_id="2026-primary",
        jurisdiction_id="mi-washtenaw",
        source_id="washtenaw-fixture",
        fetched_at=datetime(2026, 8, 4, tzinfo=timezone.utc),
    )
    assert len(rows) == 8
    alpha = [r for r in rows if r.choice_name == "Alpha"]
    assert all(r.reporting_unit_name == "City of Ann Arbor, Ward 1, Precinct 2" for r in alpha)
    assert all(r.ballot_order == 1 for r in alpha)
    assert {r.vote_mode for r in alpha} == {
        VoteMode.EARLY,
        VoteMode.ABSENTEE,
        VoteMode.ELECTION_DAY,
        VoteMode.TOTAL,
    }
