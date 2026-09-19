from datetime import datetime, timezone

import pytest

from election_data_grabber.models import ResultObservation, VoteMode
from election_data_grabber.reconcile import aggregate_observations, reconcile_to_summary


def obs(unit: str, votes: int, mode: VoteMode = VoteMode.TOTAL) -> ResultObservation:
    return ResultObservation(
        election_id="2026-08-04-mi-primary",
        jurisdiction_id="mi-washtenaw",
        reporting_unit_id=unit,
        reporting_unit_name=unit,
        contest_name="Governor",
        choice_name="Candidate A",
        votes=votes,
        vote_mode=mode,
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


def test_aggregation_rejects_total_plus_components_for_same_observation_identity():
    with pytest.raises(ValueError):
        aggregate_observations([
            obs("p1", 100, VoteMode.TOTAL),
            obs("p1", 60, VoteMode.ELECTION_DAY),
            obs("p1", 40, VoteMode.ABSENTEE),
        ])


def test_aggregation_allows_component_only_modes():
    totals = aggregate_observations([
        obs("p1", 60, VoteMode.ELECTION_DAY),
        obs("p1", 40, VoteMode.ABSENTEE),
    ])
    assert totals[("Governor", "Candidate A", VoteMode.ELECTION_DAY)] == 60
    assert totals[("Governor", "Candidate A", VoteMode.ABSENTEE)] == 40
