from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field, HttpUrl


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


class ResultObservation(BaseModel):
    election_id: str
    jurisdiction_id: str
    reporting_unit_id: str
    reporting_unit_name: str
    contest_id: str | None = None
    contest_name: str
    choice_id: str | None = None
    choice_name: str
    ballot_order: int | None = None
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
