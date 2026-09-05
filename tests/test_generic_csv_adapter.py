from datetime import datetime, timezone
from pathlib import Path

from election_data_grabber.adapters.generic_csv import parse_generic_precinct_csv
from election_data_grabber.models import VoteMode


def test_generic_csv_preserves_vote_modes():
    body = Path("tests/fixtures/generic_precinct_modes.csv").read_bytes()
    rows = parse_generic_precinct_csv(
        body,
        election_id="2024-general",
        jurisdiction_id="example",
        source_id="fixture",
        fetched_at=datetime(2024, 11, 5, tzinfo=timezone.utc),
    )

    assert len(rows) == 8
    alpha = [r for r in rows if r.choice_name == "Alpha"]
    assert {r.vote_mode for r in alpha} == {
        VoteMode.TOTAL,
        VoteMode.ELECTION_DAY,
        VoteMode.ABSENTEE,
        VoteMode.EARLY,
    }
    assert next(r for r in alpha if r.vote_mode == VoteMode.TOTAL).votes == 120
