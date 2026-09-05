from datetime import datetime, timezone

from election_data_grabber.adapters.generic_json import parse_generic_results_json
from election_data_grabber.models import VoteMode


def test_generic_json_preserves_order_party_and_mode():
    payload = {
        "reporting_units": [
            {
                "id": "p1",
                "name": "Ward 1 Precinct 1",
                "contests": [
                    {
                        "name": "Mayor",
                        "choices": [
                            {"name": "Alpha", "party": "DEM", "order": 1, "votes": 101, "mode": "early"},
                            {"name": "Beta", "party": "REP", "order": 2, "votes": 99, "mode": "early"},
                        ],
                    }
                ],
            }
        ]
    }
    rows = parse_generic_results_json(
        payload,
        election_id="2026-general",
        jurisdiction_id="example",
        source_id="fixture-json",
        fetched_at=datetime(2026, 11, 3, tzinfo=timezone.utc),
    )
    assert len(rows) == 2
    assert rows[0].ballot_order == 1
    assert rows[0].party == "DEM"
    assert rows[0].vote_mode == VoteMode.EARLY
    assert rows[1].ballot_order == 2
