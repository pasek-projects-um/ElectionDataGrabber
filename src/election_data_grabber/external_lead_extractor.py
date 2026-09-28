from __future__ import annotations

import re
from dataclasses import replace
from urllib.parse import urlparse

from election_data_grabber.external_source_leads import (
    ExternalLeadOrigin,
    ExternalSourceLead,
    OfficialStatus,
)

URL_RE=re.compile(r"https?://[^\s\"'<>)]+")


def extract_http_urls(text: str) -> list[str]:
    seen=set()
    out=[]
    for match in URL_RE.findall(text):
        url=match.rstrip(".,;:")
        if url not in seen:
            seen.add(url)
            out.append(url)
    return out


def classify_candidate_url(url: str) -> OfficialStatus:
    host=(urlparse(url).hostname or "").lower()
    if host.endswith(".gov") or host == "gov":
        return OfficialStatus.LIKELY_OFFICIAL
    return OfficialStatus.UNKNOWN


def leads_from_repository_text(
    text: str,
    *,
    source_record_prefix: str,
    origin_locator: str,
    jurisdiction_id: str="",
    source_role: str="",
    origin: ExternalLeadOrigin=ExternalLeadOrigin.RESEARCH_REPOSITORY,
) -> list[ExternalSourceLead]:
    leads=[]
    for i,url in enumerate(extract_http_urls(text), start=1):
        leads.append(ExternalSourceLead(
            source_record_id=f"{source_record_prefix}:{i}",
            jurisdiction_id=jurisdiction_id,
            lead_url=url,
            origin=origin,
            origin_locator=origin_locator,
            official_status=classify_candidate_url(url),
            source_role=source_role,
            notes="Candidate lead extracted from external repository text; official status requires direct verification.",
        ))
    return leads
