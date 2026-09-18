from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from datetime import date
from enum import StrEnum

SAFE = re.compile(r"[^a-z0-9]+")


def _token(value: str) -> str:
    value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode()
    return SAFE.sub("-", value.lower()).strip("-")


class UnitType(StrEnum):
    PRECINCT = "precinct"
    WARD = "ward"
    MUNICIPALITY = "municipality"
    COUNTY = "county"
    COUNTY_EQUIVALENT = "county_equivalent"
    REPORTING_UNIT = "reporting_unit"
    SUBUNIT = "subunit"
    EARLY_VOTE_CENTER = "early_vote_center"
    ABSENTEE_COUNTING_BOARD = "absentee_counting_board"
    MULTI_PRECINCT_AVCB = "multi_precinct_avcb"
    VOTE_CENTER = "vote_center"
    SYNTHETIC_REPORTING_UNIT = "synthetic_reporting_unit"
    UNKNOWN = "unknown"


class AggregationScope(StrEnum):
    PRECINCT = "precinct"
    WARD = "ward"
    MUNICIPALITY = "municipality"
    COUNTY = "county"
    MULTI_PRECINCT = "multi_precinct"
    VOTE_CENTER = "vote_center"
    STATE = "state"
    UNKNOWN = "unknown"


class AllocationSemantics(StrEnum):
    NATIVE_TO_PRECINCT = "native_to_precinct"
    REASSIGNED_TO_PRECINCT = "reassigned_to_precinct"
    AGGREGATED_MULTI_PRECINCT = "aggregated_multi_precinct"
    MUNICIPALITYWIDE = "municipalitywide"
    COUNTYWIDE = "countywide"
    SOURCE_NATIVE_NON_GEOGRAPHIC = "source_native_non_geographic"
    SYNTHETIC_REPORTING_UNIT = "synthetic_reporting_unit"
    UNKNOWN = "unknown"


class IdentityStatus(StrEnum):
    AUTHORITATIVE_SOURCE_NATIVE = "authoritative_source_native"
    AUTHORITATIVE_GEOGRAPHIC = "authoritative_geographic"
    PROVISIONAL = "provisional"
    SYNTHETIC = "synthetic"


class ReconciliationStatus(StrEnum):
    MATCHED_EXACT = "matched_exact"
    MATCHED_HIGH_CONFIDENCE = "matched_high_confidence"
    AMBIGUOUS = "ambiguous"
    UNMATCHED = "unmatched"
    NEEDS_MANUAL_REVIEW = "needs_manual_review"


class RelationshipType(StrEnum):
    SAME_AS = "same_as"
    RENAMED_TO = "renamed_to"
    SPLIT_INTO = "split_into"
    MERGED_INTO = "merged_into"
    AGGREGATES = "aggregates"
    COMPONENT_OF = "component_of"
    REASSIGNED_TO = "reassigned_to"
    APPROXIMATE_CROSSWALK = "approximate_crosswalk"


def reporting_regime_id(jurisdiction_id: str, election_id: str, regime_kind: str, source_id: str) -> str:
    if not jurisdiction_id.startswith("us:"):
        raise ValueError("reporting regime requires canonical jurisdiction_id")
    parts = [_token(election_id), _token(regime_kind), _token(source_id)]
    if not all(parts):
        raise ValueError("election_id, regime_kind, and source_id are required")
    return f"{jurisdiction_id}:election:{parts[0]}:regime:{parts[1]}:{parts[2]}"


def reporting_unit_id(
    state: str,
    election_id: str,
    reporting_regime_id: str,
    unit_type: UnitType,
    raw_name: str,
    source_native_id: str = "",
) -> str:
    st = state.strip().upper()
    if not re.fullmatch(r"[A-Z]{2}", st):
        raise ValueError("invalid state abbreviation")
    election = _token(election_id)
    key = _token(source_native_id) if source_native_id.strip() else _token(raw_name)
    regime = _token(reporting_regime_id)
    if not election or not regime or not key:
        raise ValueError("election, regime, and source identity are required")
    return f"us:{st.lower()}:election:{election}:reporting-unit:{unit_type.value}:{regime}:{key}"


@dataclass(frozen=True, slots=True)
class ReportingRegime:
    reporting_regime_id: str
    election_id: str
    jurisdiction_id: str
    authority_id: str
    source_id: str
    source_capability_type: str
    regime_kind: str
    snapshot_sha256: str

    def __post_init__(self) -> None:
        if not self.jurisdiction_id.startswith("us:"):
            raise ValueError("jurisdiction_id must be canonical")
        if not self.authority_id.startswith("us:authority:"):
            raise ValueError("authority_id must be independent")
        if len(self.snapshot_sha256) != 64:
            raise ValueError("reporting regime requires immutable snapshot SHA-256")


@dataclass(frozen=True, slots=True)
class CanonicalReportingUnit:
    reporting_unit_id: str
    election_id: str
    jurisdiction_id: str
    authority_id: str
    source_id: str
    source_capability_type: str
    reporting_regime_id: str
    unit_type: UnitType
    canonical_name: str
    raw_name: str
    snapshot_sha256: str
    source_native_id: str | None = None
    parent_reporting_unit_id: str | None = None
    aggregation_scope: AggregationScope = AggregationScope.UNKNOWN
    allocation_semantics: AllocationSemantics = AllocationSemantics.UNKNOWN
    identity_status: IdentityStatus = IdentityStatus.PROVISIONAL
    reconciliation_status: ReconciliationStatus = ReconciliationStatus.UNMATCHED
    effective_from: date | None = None
    effective_to: date | None = None

    def __post_init__(self) -> None:
        if self.effective_from and self.effective_to and self.effective_to < self.effective_from:
            raise ValueError("effective_to cannot precede effective_from")
        if len(self.snapshot_sha256) != 64:
            raise ValueError("reporting unit requires immutable snapshot SHA-256")
        if self.identity_status == IdentityStatus.AUTHORITATIVE_SOURCE_NATIVE and not self.source_native_id:
            raise ValueError("source-native identity requires source_native_id")


@dataclass(frozen=True, slots=True)
class ReportingUnitCrosswalk:
    from_reporting_unit_id: str
    to_reporting_unit_id: str
    relationship_type: RelationshipType
    evidence_source_id: str
    evidence_snapshot_sha256: str
    weight: float | None = None
    weight_basis: str | None = None
    effective_from: date | None = None
    effective_to: date | None = None
    reconciliation_status: ReconciliationStatus = ReconciliationStatus.NEEDS_MANUAL_REVIEW
    note: str | None = None

    def __post_init__(self) -> None:
        if self.from_reporting_unit_id == self.to_reporting_unit_id:
            raise ValueError("crosswalk endpoints must be distinct historical identities")
        if len(self.evidence_snapshot_sha256) != 64:
            raise ValueError("crosswalk requires immutable evidence snapshot")
        if self.weight is not None and not 0 <= self.weight <= 1:
            raise ValueError("weight must be between zero and one")
        if self.weight is not None and not self.weight_basis:
            raise ValueError("weighted crosswalk requires weight_basis")
        if self.effective_from and self.effective_to and self.effective_to < self.effective_from:
            raise ValueError("effective_to cannot precede effective_from")


def validate_reporting_unit_crosswalks(rows: list[ReportingUnitCrosswalk]) -> None:
    seen: set[tuple[str, str, RelationshipType, date | None, date | None]] = set()
    for row in rows:
        key = (row.from_reporting_unit_id, row.to_reporting_unit_id, row.relationship_type, row.effective_from, row.effective_to)
        if key in seen:
            raise ValueError(f"duplicate reporting-unit crosswalk: {key}")
        seen.add(key)
