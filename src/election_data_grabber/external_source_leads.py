from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class ExternalLeadOrigin(StrEnum):
    RESEARCH_REPOSITORY = "research_repository"
    HISTORICAL_ARCHIVE = "historical_archive"
    SCRAPER_REPOSITORY = "scraper_repository"
    OFFICIAL_DIRECTORY_REFERENCE = "official_directory_reference"


class OfficialStatus(StrEnum):
    VERIFIED_OFFICIAL = "verified_official"
    LIKELY_OFFICIAL = "likely_official"
    THIRD_PARTY_REFERENCE = "third_party_reference"
    UNKNOWN = "unknown"


@dataclass(frozen=True, slots=True)
class ExternalSourceLead:
    source_record_id: str
    jurisdiction_id: str
    lead_url: str
    origin: ExternalLeadOrigin
    origin_locator: str
    official_status: OfficialStatus = OfficialStatus.UNKNOWN
    source_role: str = ""
    artifact_type: str = ""
    family_hint: str = ""
    discovered_at: str = ""
    upstream_commit: str = ""
    notes: str = ""

    def __post_init__(self) -> None:
        if not self.source_record_id:
            raise ValueError("source_record_id is required")
        if not self.lead_url.startswith(("http://", "https://")):
            raise ValueError("lead_url must be an HTTP(S) URL")
        if self.official_status == OfficialStatus.VERIFIED_OFFICIAL and self.origin in {
            ExternalLeadOrigin.RESEARCH_REPOSITORY,
            ExternalLeadOrigin.SCRAPER_REPOSITORY,
        }:
            if not self.notes:
                raise ValueError("verified official leads from third-party repositories require verification notes")


def dedupe_external_leads(leads: list[ExternalSourceLead]) -> list[ExternalSourceLead]:
    seen: set[tuple[str, str, str]] = set()
    out: list[ExternalSourceLead] = []
    for lead in leads:
        key=(lead.jurisdiction_id, lead.lead_url, lead.source_role)
        if key in seen:
            continue
        seen.add(key)
        out.append(lead)
    return out
