from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from math import sqrt


class OverlapRelationship(StrEnum):
    PROBABLE_MIRROR = "probable_mirror"
    PARTIAL_OVERLAP = "partial_overlap"
    COMPLEMENTARY = "complementary"
    UNCERTAIN = "uncertain"


@dataclass(frozen=True, slots=True)
class SourceSnapshot:
    source_id: str
    jurisdiction_id: str
    captured_at: str
    reporting_fraction: float | None
    result_vector: tuple[float, ...]
    reporting_units: frozenset[str] = frozenset()
    vote_modes: frozenset[str] = frozenset()

    def __post_init__(self) -> None:
        if self.reporting_fraction is not None and not 0 <= self.reporting_fraction <= 1:
            raise ValueError("reporting_fraction must be between 0 and 1")
        if not self.result_vector:
            raise ValueError("result_vector cannot be empty")


@dataclass(frozen=True, slots=True)
class OverlapCalibration:
    left_source_id: str
    right_source_id: str
    jurisdiction_id: str
    matched_snapshot_count: int
    mean_vector_similarity: float | None
    reporting_unit_jaccard: float | None
    vote_mode_jaccard: float | None
    relationship: OverlapRelationship
    residual_independence_established: bool = False
    notes: str = ""

    @property
    def safe_for_independent_evidence(self) -> bool:
        # Imperfect source correlation is not proof of orthogonal residual information.
        return self.residual_independence_established


def cosine_similarity(left: tuple[float, ...], right: tuple[float, ...]) -> float:
    if len(left) != len(right):
        raise ValueError("result vectors must have equal dimension")
    dot=sum(a*b for a,b in zip(left,right))
    lnorm=sqrt(sum(a*a for a in left))
    rnorm=sqrt(sum(b*b for b in right))
    if not lnorm or not rnorm:
        raise ValueError("result vectors must have nonzero norm")
    return dot/(lnorm*rnorm)


def jaccard(left: frozenset[str], right: frozenset[str]) -> float | None:
    union=left|right
    return len(left&right)/len(union) if union else None


def comparable_progress(left: SourceSnapshot, right: SourceSnapshot, tolerance: float = 0.05) -> bool:
    if left.jurisdiction_id != right.jurisdiction_id:
        return False
    if left.reporting_fraction is None or right.reporting_fraction is None:
        return False
    return abs(left.reporting_fraction-right.reporting_fraction) <= tolerance
