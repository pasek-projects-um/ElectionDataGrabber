from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum


class ExecutionStage(IntEnum):
    DISCOVERED = 1
    FETCHABLE = 2
    PARSER_SELECTED = 3
    PARSE_EXECUTED = 4
    NORMALIZED = 5
    REPLAY_TESTED = 6
    REFRESH_VERIFIED = 7


@dataclass(frozen=True, slots=True)
class SourceExecutionEvidence:
    state: str
    result_url: str
    access_family: str
    parser: str
    stage: ExecutionStage
    observation_count: int = 0
    smallest_observed_unit: str = "unknown"
    vote_modes_preserved: bool | None = None
    failure_class: str = ""
    snapshot_sha256: str = ""

    def validate(self) -> None:
        if self.stage >= ExecutionStage.NORMALIZED and self.observation_count <= 0:
            raise ValueError("normalized-or-higher evidence requires observations")
        if self.stage >= ExecutionStage.REPLAY_TESTED and not self.snapshot_sha256:
            raise ValueError("replay-tested evidence requires immutable snapshot provenance")
        if self.failure_class and self.stage >= ExecutionStage.NORMALIZED:
            raise ValueError("successful normalized evidence cannot carry a failure class")


def maturity_row(evidence: SourceExecutionEvidence) -> dict[str, str]:
    evidence.validate()
    return {
        "state": evidence.state,
        "result_url": evidence.result_url,
        "access_family": evidence.access_family,
        "parser": evidence.parser,
        "execution_stage": evidence.stage.name.lower(),
        "observation_count": str(evidence.observation_count),
        "smallest_observed_unit": evidence.smallest_observed_unit,
        "vote_modes_preserved": (
            "" if evidence.vote_modes_preserved is None else str(evidence.vote_modes_preserved).lower()
        ),
        "failure_class": evidence.failure_class,
        "snapshot_sha256": evidence.snapshot_sha256,
    }


def promotable_to_supported(evidence: SourceExecutionEvidence) -> bool:
    """Only executed normalization counts as supported ingestion evidence."""
    evidence.validate()
    return evidence.stage >= ExecutionStage.NORMALIZED
