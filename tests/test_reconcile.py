from datetime import datetime, timezone

from election_data_grabber.models import ResultObservation, VoteMode
from election_data_grabber.reconcile import reconcile_to_summary


def obs(unit: str, votes: int) -> ResultObservation:
    return ResultObservation(
        election_id="2026-08-04-mi-primary",
        jurisdiction_id="mi-washtenaw",
        reporting_unit_id=unit,
        reporting_unit_name=unit,
        contest_name="Governor",
        choice_name="Candidate A",
        votes=votes,
        vote_mode=VoteMode.TOTAL,
        source_id="test",
        fetched_at=datetime.now(timezone.utc),
    )


def test_reconcile_exact_total():
    results = reconcile_to_summary([obs("p1", 40), obs("p2", 60)], [obs("county", 100)])
    assert len(results) == 1
    assert results[0].precinct_sum == 100
    assert results[0].summary_total == 100
    assert results[0].residual == 0
    assert results[0].reconciles is True
