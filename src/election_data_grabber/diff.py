from __future__ import annotations

from dataclasses import dataclass

from election_data_grabber.models import ResultObservation


@dataclass(frozen=True, slots=True)
class ResultDelta:
    reporting_unit_id: str
    contest_name: str
    choice_name: str
    vote_mode: str
    old_votes: int | None
    new_votes: int
    delta: int


def observation_key(row: ResultObservation) -> tuple[str, str, str, str]:
    return (
        row.reporting_unit_id,
        row.contest_name,
        row.choice_name,
        row.vote_mode.value,
    )


def diff_observations(
    previous: list[ResultObservation], current: list[ResultObservation]
) -> list[ResultDelta]:
    old = {observation_key(row): row.votes for row in previous}
    deltas: list[ResultDelta] = []
    for row in current:
        key = observation_key(row)
        prior = old.get(key)
        if prior == row.votes:
            continue
        deltas.append(
            ResultDelta(
                reporting_unit_id=row.reporting_unit_id,
                contest_name=row.contest_name,
                choice_name=row.choice_name,
                vote_mode=row.vote_mode.value,
                old_votes=prior,
                new_votes=row.votes,
                delta=row.votes - (prior or 0),
            )
        )
    return deltas
