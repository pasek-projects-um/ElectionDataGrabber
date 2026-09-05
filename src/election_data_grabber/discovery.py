from __future__ import annotations

import re
from dataclasses import dataclass
from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup


RESULT_TERMS = re.compile(
    r"\b(election results?|unofficial results?|official results?|precinct results?|"
    r"election night|live results?|enr|statement of votes cast|sovc?|cumulative results?|"
    r"precinct summary|summary report|precinct report|precincts reported|canvass report)\b",
    re.IGNORECASE,
)


@dataclass(frozen=True, slots=True)
class CandidateSource:
    url: str
    label: str
    platform: str | None = None


def fingerprint_platform(url: str, html: str = "") -> str | None:
    blob = f"{url}\n{html}".lower()
    if "results.enr.clarityelections.com" in blob or "clarityelections" in blob:
        return "clarity"
    if "electionresults.ewashtenaw.org/electionreporting" in blob:
        return "washtenaw_enr"
    if "electionarchive.washtenaw.org" in blob:
        return "washtenaw_archive"
    if "scytl" in blob:
        return "scytl"
    if "electionware" in blob or "essvote" in blob:
        return "electionware"
    if "dominionvoting" in blob or "dominion voting" in blob:
        return "dominion"
    if "enhancedvoting" in blob or "enhanced voting" in blob or "app.enhancedvoting.com/results" in blob:
        return "enhanced_voting"
    if "knowink" in blob or "totalvote" in blob:
        return "knowink_totalvote"
    if "electionsource" in blob:
        return "electionsource"
    if "precincts reported" in blob and ("summary report" in blob or "precinct report" in blob):
        return "report_center_precinct_summary"
    if "statement of votes cast" in blob or "sovc" in blob:
        return "statement_of_votes_cast"
    if "cumulative results" in blob and "precinct results" in blob:
        return "cumulative_precinct_archive"
    return None


def discover_result_links(authority_url: str, timeout: float = 30.0) -> list[CandidateSource]:
    with httpx.Client(
        timeout=timeout,
        follow_redirects=True,
        headers={"User-Agent": "ElectionDataGrabber/0.1 (+research; source discovery)"},
    ) as client:
        response = client.get(authority_url)
        response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")
    found: dict[str, CandidateSource] = {}
    for a in soup.find_all("a", href=True):
        label = " ".join(a.stripped_strings)
        href = urljoin(str(response.url), a["href"])
        haystack = f"{label} {href}"
        if RESULT_TERMS.search(haystack):
            found[href] = CandidateSource(
                url=href,
                label=label,
                platform=fingerprint_platform(href, response.text),
            )

    # Keep discovery on web URLs; mailto/javascript links are never acquisition sources.
    return sorted(
        (x for x in found.values() if urlparse(x.url).scheme in {"http", "https"}),
        key=lambda x: x.url,
    )
