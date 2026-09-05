from datetime import datetime, timezone

from election_data_grabber.diff import diff_observations
from election_data_grabber.models import ResultObservation, VoteMode


def row(votes: int) -> ResultObservation:
    return ResultObservation(
        election_id="2026-08-04-mi-primary",
        jurisdiction_id="mi-washtenaw",
        reporting_unit_id="ann-arbor-w1-p2",
        reporting_unit_name="City of Ann Arbor, Ward 1, Precinct 2",
        contest_name="Governor DEM",
        choice_name="Jocelyn Benson",
        ballot_order=1,
        votes=votes,
        vote_mode=VoteMode.ABSENTEE,
        source_id="mi-washtenaw-live",
        fetched_at=datetime(2026, 8, 4, 21, 0, tzinfo=timezone.utc),
    )


def test_diff_emits_only_changes():
    assert diff_observations([row(210)], [row(210)]) == []
    delta = diff_observations([row(197)], [row(210)])[0]
    assert delta.old_votes == 197
    assert delta.new_votes == 210
    assert delta.delta == 13
