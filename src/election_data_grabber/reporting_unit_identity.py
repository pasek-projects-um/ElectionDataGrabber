from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from datetime import date
from enum import StrEnum

SAFE = re.compile(r"[^a-z0-9]+")
SHA256 = re.compile(r"^[0-9a-fA-F]{64}$")


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


class GeographicRelationshipType(StrEnum):
    EXACT = "exact"
    AGGREGATE_OF = "aggregate_of"
    COMPONENT_OF = "component_of"
    SPLIT_ACROSS = "split_across"
    MERGED_FROM = "merged_from"
    REASSIGNED = "reassigned"
    SYNTHETIC_NON_GEOGRAPHIC = "synthetic_non_geographic"
    APPROXIMATE = "approximate"
    UNKNOWN = "unknown"


@dataclass(frozen=True, slots=True)
class ReportingContextSpec:
    state: str
    election_id: str
    jurisdiction_id: str
    authority_id: str
    source_id: str
    source_capability_type: str
    regime_kind: str

    @classmethod
    def from_source_capability(cls, *, state: str, election_id: str, regime_kind: str, capability: object) -> "ReportingContextSpec":
        if not getattr(capability, "is_positive", False):
            raise ValueError("reporting context requires positively adjudicated source capability")
        capability_type = str(getattr(capability, "capability_type", ""))
        if regime_kind == "election-night" and capability_type != "election_night":
            raise ValueError("election-night regime requires election-night source capability")
        if regime_kind in {"certified", "final"} and capability_type != "final":
            raise ValueError("certified/final regime requires final source capability")
        return cls(
            state, election_id, getattr(capability, "jurisdiction_id"),
            getattr(capability, "authority_id"), getattr(capability, "source_id"),
            capability_type, regime_kind,
        )

    def for_snapshot(self, snapshot_sha256: str) -> "AdapterReportingContext":
        return AdapterReportingContext(
            self.state, self.election_id, self.jurisdiction_id, self.authority_id,
            self.source_id, self.source_capability_type, self.regime_kind, snapshot_sha256,
        )


@dataclass(frozen=True, slots=True)
class AdapterReportingContext:
    state: str
    election_id: str
    jurisdiction_id: str
    authority_id: str
    source_id: str
    source_capability_type: str
    regime_kind: str
    snapshot_sha256: str

    def __post_init__(self) -> None:
        if not self.jurisdiction_id.startswith("us:"):
            raise ValueError("adapter reporting context requires canonical jurisdiction_id")
        if not self.authority_id.startswith("us:authority:"):
            raise ValueError("adapter reporting context requires independent authority_id")
        if not SHA256.fullmatch(self.snapshot_sha256):
            raise ValueError("adapter reporting context requires immutable snapshot SHA-256")
        if not self.source_id.strip() or not self.source_capability_type.strip() or not self.regime_kind.strip():
            raise ValueError("source identity, capability, and regime kind are required")

    @property
    def regime_id(self) -> str:
        return reporting_regime_id(self.jurisdiction_id, self.election_id, self.regime_kind, self.source_id)

    def validate_call(self, *, election_id: str, source_id: str) -> None:
        if election_id != self.election_id:
            raise ValueError("reporting context election_id disagrees with adapter call")
        if source_id != self.source_id:
            raise ValueError("reporting context source_id disagrees with adapter call")

    def unit_id(self, unit_type: UnitType, raw_name: str, source_native_id: str = "") -> str:
        return reporting_unit_id(self.state, self.election_id, self.regime_id, unit_type, raw_name, source_native_id)

    @classmethod
    def from_source_capability(cls, *, state: str, election_id: str, regime_kind: str, snapshot_sha256: str, capability: object) -> "AdapterReportingContext":
        if not getattr(capability, "is_positive", False):
            raise ValueError("reporting context requires positively adjudicated source capability")
        capability_type = str(getattr(capability, "capability_type", ""))
        if regime_kind == "election-night" and capability_type != "election_night":
            raise ValueError("election-night regime requires election-night source capability")
        if regime_kind in {"certified", "final"} and capability_type != "final":
            raise ValueError("certified/final regime requires final source capability")
        return cls(
            state=state, election_id=election_id,
            jurisdiction_id=getattr(capability, "jurisdiction_id"),
            authority_id=getattr(capability, "authority_id"),
            source_id=getattr(capability, "source_id"),
            source_capability_type=capability_type, regime_kind=regime_kind,
            snapshot_sha256=snapshot_sha256,
        )


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
        expected = reporting_regime_id(self.jurisdiction_id, self.election_id, self.regime_kind, self.source_id)
        if self.reporting_regime_id != expected:
            raise ValueError("reporting_regime_id disagrees with regime components")
        if not self.authority_id.startswith("us:authority:"):
            raise ValueError("authority_id must be independent")
        if not SHA256.fullmatch(self.snapshot_sha256):
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
        if not SHA256.fullmatch(self.snapshot_sha256):
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
        if not SHA256.fullmatch(self.evidence_snapshot_sha256):
            raise ValueError("crosswalk requires immutable evidence snapshot")
        if self.weight is not None and not 0 <= self.weight <= 1:
            raise ValueError("weight must be between zero and one")
        if self.weight is not None and not self.weight_basis:
            raise ValueError("weighted crosswalk requires weight_basis")
        if self.effective_from and self.effective_to and self.effective_to < self.effective_from:
            raise ValueError("effective_to cannot precede effective_from")


@dataclass(frozen=True, slots=True)
class ReportingUnitGeographicCrosswalk:
    reporting_unit_id: str
    geographic_unit_id: str | None
    relationship_type: GeographicRelationshipType
    evidence_source_id: str
    evidence_snapshot_sha256: str
    effective_from: date | None = None
    effective_to: date | None = None
    allocation_weight: float | None = None
    weight_basis: str | None = None
    note: str | None = None

    def __post_init__(self) -> None:
        if self.relationship_type == GeographicRelationshipType.SYNTHETIC_NON_GEOGRAPHIC:
            if self.geographic_unit_id:
                raise ValueError("synthetic/non-geographic reporting unit cannot claim geographic identity")
        elif not self.geographic_unit_id:
            raise ValueError("geographic relationship requires geographic_unit_id")
        if not SHA256.fullmatch(self.evidence_snapshot_sha256):
            raise ValueError("geographic crosswalk requires immutable evidence snapshot")
        if self.allocation_weight is not None:
            if not 0 <= self.allocation_weight <= 1:
                raise ValueError("allocation_weight must be between zero and one")
            if not self.weight_basis:
                raise ValueError("weighted geographic crosswalk requires weight_basis")
            if self.relationship_type in {GeographicRelationshipType.EXACT, GeographicRelationshipType.SYNTHETIC_NON_GEOGRAPHIC}:
                raise ValueError("exact/non-geographic relationships must not invent allocation weights")
        if self.effective_from and self.effective_to and self.effective_to < self.effective_from:
            raise ValueError("effective_to cannot precede effective_from")


def _overlap(a_start: date | None, a_end: date | None, b_start: date | None, b_end: date | None) -> bool:
    return max(a_start or date.min, b_start or date.min) <= min(a_end or date.max, b_end or date.max)


def validate_reporting_unit_crosswalks(rows: list[ReportingUnitCrosswalk]) -> None:
    seen: set[tuple[str, str, RelationshipType, date | None, date | None]] = set()
    for row in rows:
        key = (row.from_reporting_unit_id, row.to_reporting_unit_id, row.relationship_type, row.effective_from, row.effective_to)
        if key in seen:
            raise ValueError(f"duplicate reporting-unit crosswalk: {key}")
        seen.add(key)


def validate_reporting_unit_geographic_crosswalks(rows: list[ReportingUnitGeographicCrosswalk]) -> None:
    seen: set[tuple[object, ...]] = set()
    groups: dict[tuple[str, str | None], list[ReportingUnitGeographicCrosswalk]] = {}
    for row in rows:
        key = (
            row.reporting_unit_id, row.geographic_unit_id, row.relationship_type,
            row.effective_from, row.effective_to,
        )
        if key in seen:
            raise ValueError(f"duplicate reporting-unit/geography crosswalk: {key}")
        seen.add(key)
        groups.setdefault((row.reporting_unit_id, row.geographic_unit_id), []).append(row)

    for key, items in groups.items():
        for i, left in enumerate(items):
            for right in items[i + 1:]:
                if _overlap(left.effective_from, left.effective_to, right.effective_from, right.effective_to):
                    if left.relationship_type != right.relationship_type:
                        raise ValueError(f"conflicting geographic relationships in overlapping periods: {key}")

    # Some semantics are exclusive at the reporting-unit level, not merely for
    # a reporting/geographic pair. An exact unit cannot simultaneously be exact
    # to two different geographies, and a synthetic/non-geographic unit cannot
    # acquire geography during the same effective interval.
    by_reporting_unit: dict[str, list[ReportingUnitGeographicCrosswalk]] = {}
    for row in rows:
        by_reporting_unit.setdefault(row.reporting_unit_id, []).append(row)
    for reporting_unit_id, items in by_reporting_unit.items():
        for i, left in enumerate(items):
            for right in items[i + 1:]:
                if not _overlap(left.effective_from, left.effective_to, right.effective_from, right.effective_to):
                    continue
                types = {left.relationship_type, right.relationship_type}
                if GeographicRelationshipType.SYNTHETIC_NON_GEOGRAPHIC in types and len(types) > 1:
                    raise ValueError(f"non-geographic unit has overlapping geographic mapping: {reporting_unit_id}")
                if (
                    left.relationship_type == right.relationship_type == GeographicRelationshipType.EXACT
                    and left.geographic_unit_id != right.geographic_unit_id
                ):
                    raise ValueError(f"exact reporting unit maps to multiple geographies: {reporting_unit_id}")
