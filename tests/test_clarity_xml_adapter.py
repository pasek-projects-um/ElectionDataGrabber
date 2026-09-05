from datetime import datetime, timezone
from pathlib import Path

from election_data_grabber.adapters.clarity_xml import parse_clarity_like_xml
from election_data_grabber.models import VoteMode


def test_clarity_like_xml_extracts_order_party_and_modes():
    rows = parse_clarity_like_xml(
        Path("tests/fixtures/clarity_like.xml").read_bytes(),
        election_id="2026-general",
        jurisdiction_id="example",
        source_id="clarity-fixture",
        fetched_at=datetime(2026, 11, 3, tzinfo=timezone.utc),
    )
    assert len(rows) == 8
    alpha = [r for r in rows if r.choice_name == "Alpha"]
    assert all(r.ballot_order == 1 for r in alpha)
    assert all(r.party == "DEM" for r in alpha)
    assert {r.vote_mode for r in alpha} == {
        VoteMode.ELECTION_DAY,
        VoteMode.EARLY,
        VoteMode.ABSENTEE,
        VoteMode.TOTAL,
    }
