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


@dataclass(frozen=True, slots=True)
class MatchedSnapshotPair:
    left: SourceSnapshot
    right: SourceSnapshot
    progress_distance: float
    vector_similarity: float
    reporting_unit_jaccard: float | None
    vote_mode_jaccard: float | None


def match_snapshots(
    left_snapshots: list[SourceSnapshot],
    right_snapshots: list[SourceSnapshot],
    tolerance: float = 0.05,
) -> list[MatchedSnapshotPair]:
    pairs: list[MatchedSnapshotPair] = []
    for left in left_snapshots:
        candidates = [
            right for right in right_snapshots
            if comparable_progress(left, right, tolerance=tolerance)
        ]
        if not candidates:
            continue
        right = min(
            candidates,
            key=lambda r: abs((left.reporting_fraction or 0.0) - (r.reporting_fraction or 0.0)),
        )
        pairs.append(
            MatchedSnapshotPair(
                left=left,
                right=right,
                progress_distance=abs((left.reporting_fraction or 0.0) - (right.reporting_fraction or 0.0)),
                vector_similarity=cosine_similarity(left.result_vector, right.result_vector),
                reporting_unit_jaccard=jaccard(left.reporting_units, right.reporting_units),
                vote_mode_jaccard=jaccard(left.vote_modes, right.vote_modes),
            )
        )
    return pairs


def summarize_overlap(
    left_source_id: str,
    right_source_id: str,
    jurisdiction_id: str,
    pairs: list[MatchedSnapshotPair],
) -> OverlapCalibration:
    if not pairs:
        return OverlapCalibration(
            left_source_id,
            right_source_id,
            jurisdiction_id,
            0,
            None,
            None,
            None,
            OverlapRelationship.UNCERTAIN,
        )
    mean_similarity=sum(p.vector_similarity for p in pairs)/len(pairs)
    ru=[p.reporting_unit_jaccard for p in pairs if p.reporting_unit_jaccard is not None]
    vm=[p.vote_mode_jaccard for p in pairs if p.vote_mode_jaccard is not None]
    mean_ru=sum(ru)/len(ru) if ru else None
    mean_vm=sum(vm)/len(vm) if vm else None
    if mean_similarity >= 0.995 and (mean_ru is None or mean_ru >= 0.9):
        relationship=OverlapRelationship.PROBABLE_MIRROR
    elif (mean_ru is not None and mean_ru > 0) or (mean_vm is not None and mean_vm > 0):
        relationship=OverlapRelationship.PARTIAL_OVERLAP
    else:
        relationship=OverlapRelationship.UNCERTAIN
    return OverlapCalibration(
        left_source_id,
        right_source_id,
        jurisdiction_id,
        len(pairs),
        mean_similarity,
        mean_ru,
        mean_vm,
        relationship,
    )
