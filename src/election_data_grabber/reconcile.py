from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass

from election_data_grabber.models import ResultObservation, VoteMode


@dataclass(slots=True)
class ReconciliationResult:
    contest_name: str
    choice_name: str
    vote_mode: VoteMode
    precinct_sum: int
    summary_total: int
    residual: int

    @property
    def reconciles(self) -> bool:
        return self.residual == 0


def aggregate_observations(
    observations: list[ResultObservation],
) -> dict[tuple[str, str, VoteMode], int]:
    totals: dict[tuple[str, str, VoteMode], int] = defaultdict(int)
    for obs in observations:
        totals[(obs.contest_name, obs.choice_name, obs.vote_mode)] += obs.votes
    return dict(totals)


def reconcile_to_summary(
    precinct_observations: list[ResultObservation],
    summary_observations: list[ResultObservation],
) -> list[ReconciliationResult]:
    precinct_totals = aggregate_observations(precinct_observations)
    summary_totals = aggregate_observations(summary_observations)
    results: list[ReconciliationResult] = []

    for key, summary_total in sorted(
        summary_totals.items(), key=lambda item: (item[0][0], item[0][1], item[0][2].value)
    ):
        precinct_sum = precinct_totals.get(key, 0)
        results.append(
            ReconciliationResult(
                contest_name=key[0],
                choice_name=key[1],
                vote_mode=key[2],
                precinct_sum=precinct_sum,
                summary_total=summary_total,
                residual=precinct_sum - summary_total,
            )
        )
    return results
