from __future__ import annotations

from datetime import datetime
import re
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field, HttpUrl, model_validator


class SourceKind(StrEnum):
    OFFICIAL_API = "official_api"
    OFFICIAL_DOWNLOAD = "official_download"
    OFFICIAL_WEB = "official_web"
    VENDOR = "vendor"
    OPEN_DATA = "open_data"
    MEDIA = "media"
    ARCHIVE = "archive"


class Format(StrEnum):
    JSON = "json"
    XML = "xml"
    CSV = "csv"
    XLSX = "xlsx"
    HTML = "html"
    PDF = "pdf"
    ZIP = "zip"
    UNKNOWN = "unknown"


class VoteMode(StrEnum):
    TOTAL = "total"
    ELECTION_DAY = "election_day"
    EARLY = "early"
    ABSENTEE = "absentee"
    MAIL = "mail"
    PROVISIONAL = "provisional"
    UOCAVA = "uocava"
    OTHER = "other"
    UNKNOWN = "unknown"


class Source(BaseModel):
    source_id: str
    jurisdiction: str
    state: str
    url: HttpUrl
    kind: SourceKind
    format: Format = Format.UNKNOWN
    platform: str | None = None
    official: bool = False
    live_capable: bool = False
    precinct_level: bool | None = None
    vote_mode_detail: bool | None = None
    notes: str | None = None


class Snapshot(BaseModel):
    source_id: str
    fetched_at: datetime
    source_timestamp: datetime | None = None
    url: HttpUrl
    http_status: int
    content_type: str | None = None
    sha256: str
    body_path: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class ReportingUnit(BaseModel):
    reporting_unit_id: str
    election_id: str
    name: str
    unit_type: str = "precinct"
    state: str
    county: str | None = None
    municipality: str | None = None
    ward: str | None = None
    precinct: str | None = None
    polling_place_name: str | None = None
    polling_place_address: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    registered_voters: int | None = None
    source_id: str
    raw_name: str | None = None


class ContestChoice(BaseModel):
    election_id: str
    contest_id: str
    choice_id: str
    choice_name: str
    ballot_order: int | None = None
    party: str | None = None
    incumbent: bool | None = None
    write_in: bool | None = None
    source_id: str
    raw_choice_name: str | None = None


class BallotSummary(BaseModel):
    election_id: str
    jurisdiction_id: str
    reporting_unit_id: str | None = None
    party: str | None = None
    vote_mode: VoteMode = VoteMode.TOTAL
    ballots_cast: int | None = None
    ballots_issued: int | None = None
    registered_voters: int | None = None
    source_id: str
    fetched_at: datetime
    source_timestamp: datetime | None = None
    raw_label: str | None = None


class ReportingProgressKind(StrEnum):
    UNIT_EXISTS = "unit_exists"
    UNIT_REPORTED = "unit_reported"
    SOURCE_COMPLETE = "source_complete"
    EXPECTED_COMPONENTS = "expected_components"
    SOURCE_COUNTS = "source_counts"


class ReportingProgressBasis(StrEnum):
    SOURCE_REPORTED = "source_reported"
    INFERRED = "inferred"
    UNKNOWN = "unknown"


class UpdateSemantics(StrEnum):
    CUMULATIVE = "cumulative"
    INCREMENTAL = "incremental"
    UNKNOWN = "unknown"


class ReportingProgressScope(StrEnum):
    SOURCE = "source"
    REPORTING_UNIT = "reporting_unit"
    CONTEST = "contest"


class ReportingProgress(BaseModel):
    election_id: str
    jurisdiction_id: str
    source_id: str
    fetched_at: datetime
    reporting_regime_id: str | None = None
    reporting_unit_id: str | None = None
    reporting_unit_name: str | None = None
    contest_id: str | None = None
    scope: ReportingProgressScope
    kind: ReportingProgressKind
    basis: ReportingProgressBasis
    update_semantics: UpdateSemantics = UpdateSemantics.UNKNOWN
    reported: bool | None = None
    complete: bool | None = None
    reporting_count: int | None = None
    expected_count: int | None = None
    expected_components: list[str] | None = None
    observed_components: list[str] | None = None
    source_timestamp: datetime | None = None
    snapshot_sha256: str | None = None
    raw_status: str | None = None

    @model_validator(mode="after")
    def validate_progress(self) -> "ReportingProgress":
        if self.scope == ReportingProgressScope.REPORTING_UNIT and not self.reporting_unit_id:
            raise ValueError("reporting-unit progress requires reporting_unit_id")
        if self.scope == ReportingProgressScope.SOURCE and self.reporting_unit_id is not None:
            raise ValueError("source-scope progress cannot carry reporting_unit_id")
        if self.scope == ReportingProgressScope.CONTEST and not self.contest_id:
            raise ValueError("contest-scope progress requires contest_id")
        if self.scope != ReportingProgressScope.CONTEST and self.contest_id is not None:
            raise ValueError("contest_id is only valid at contest scope")
        if self.reporting_count is not None and self.reporting_count < 0:
            raise ValueError("reporting_count cannot be negative")
        if self.expected_count is not None and self.expected_count < 0:
            raise ValueError("expected_count cannot be negative")
        if self.kind == ReportingProgressKind.SOURCE_COUNTS and self.reporting_count is None and self.expected_count is None:
            raise ValueError("source counts require reporting_count or expected_count")
        if self.kind != ReportingProgressKind.SOURCE_COUNTS and (self.reporting_count is not None or self.expected_count is not None):
            raise ValueError("reporting/expected counts are only valid for source-count progress")
        if self.kind == ReportingProgressKind.SOURCE_COMPLETE and self.complete is None:
            raise ValueError("source completion requires complete")
        if self.kind != ReportingProgressKind.SOURCE_COMPLETE and self.complete is not None:
            raise ValueError("complete is only valid for source-completion progress")
        if self.kind in {ReportingProgressKind.UNIT_EXISTS, ReportingProgressKind.UNIT_REPORTED} and self.reported is None:
            raise ValueError("unit existence/reporting requires reported")
        if self.kind not in {ReportingProgressKind.UNIT_EXISTS, ReportingProgressKind.UNIT_REPORTED} and self.reported is not None:
            raise ValueError("reported is only valid for unit existence/reporting progress")
        if self.kind == ReportingProgressKind.EXPECTED_COMPONENTS and self.expected_components is None:
            raise ValueError("expected-components progress requires expected_components")
        if self.kind != ReportingProgressKind.EXPECTED_COMPONENTS and (self.expected_components is not None or self.observed_components is not None):
            raise ValueError("component lists are only valid for expected-components progress")
        if self.snapshot_sha256 is not None and not re.fullmatch(r"[0-9a-fA-F]{64}", self.snapshot_sha256):
            raise ValueError("reporting progress snapshot_sha256 must be a SHA-256")
        if self.basis == ReportingProgressBasis.SOURCE_REPORTED and self.raw_status is None and self.kind == ReportingProgressKind.SOURCE_COMPLETE:
            raise ValueError("source-reported completion requires raw_status provenance")
        return self


class ResultObservation(BaseModel):
    election_id: str
    jurisdiction_id: str
    reporting_unit_id: str
    reporting_unit_name: str
    reporting_regime_id: str | None = None
    reporting_unit_raw_name: str | None = None
    reporting_unit_source_native_id: str | None = None
    contest_id: str | None = None
    contest_name: str
    choice_id: str | None = None
    choice_name: str
    ballot_order: int | None = None
    ballot_order_scope: str | None = None
    # Order in a results artifact is preserved separately from verified ballot
    # position. Results-column order must not be treated as voter-facing order
    # unless the source is explicitly a ballot/rotation record.
    source_order: int | None = None
    party: str | None = None
    votes: int
    vote_mode: VoteMode = VoteMode.TOTAL
    source_id: str
    fetched_at: datetime
    source_timestamp: datetime | None = None
    registered_voters: int | None = None
    ballots_cast: int | None = None
    precincts_reporting: int | None = None
    precincts_total: int | None = None
    raw_vote_mode: str | None = None
    vote_mode_mapping_method: str | None = None
    vote_mode_evidence_reference: str | None = None
    # Optional until all adapters parse from a persisted Snapshot; audit requires
    # this to become mandatory at the normalized persistence boundary.
    snapshot_sha256: str | None = None

    @model_validator(mode="after")
    def validate_topology_provenance(self) -> "ResultObservation":
        topology_fields = (
            self.reporting_regime_id,
            self.reporting_unit_raw_name,
            self.reporting_unit_source_native_id,
        )
        if any(value is not None for value in topology_fields):
            if not self.reporting_regime_id:
                raise ValueError("canonical topology metadata requires reporting_regime_id")
            if not self.snapshot_sha256 or not re.fullmatch(r"[0-9a-fA-F]{64}", self.snapshot_sha256):
                raise ValueError("canonical topology metadata requires immutable snapshot SHA-256")
            if not self.jurisdiction_id.startswith("us:"):
                raise ValueError("canonical topology metadata requires canonical jurisdiction_id")
        return self
