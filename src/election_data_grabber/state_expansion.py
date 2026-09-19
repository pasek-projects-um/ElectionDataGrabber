from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urlparse


@dataclass(frozen=True, slots=True)
class StateExpansionProfile:
    state: str
    authority_model: str
    primary_unit: str
    central_strategy: str
    expected_units: int
    priority_families: tuple[str, ...]


PROFILES: dict[str, StateExpansionProfile] = {
    "AL": StateExpansionProfile("AL","county","county","central_local_election_officials",67,("unknown_web","pdf","civicplus")),
    "AK": StateExpansionProfile("AK","state/election-region","election_region","statewide_results",40,("state_results","pdf","csv")),
    "GA": StateExpansionProfile("GA","county","county","central_county_election_offices",159,("enhanced_voting","clarity","unknown_web")),
    "KS": StateExpansionProfile("KS","county","county","central_county_election_officers",105,("clarity","scytl","pdf")),
    "LA": StateExpansionProfile("LA","parish","parish","central_parish_directory",64,("scytl","clarity","pdf")),
    "MA": StateExpansionProfile("MA","municipal","municipality","central_local_election_offices",351,("pdf","csv","unknown_web")),
    "ND": StateExpansionProfile("ND","county","county","central_county_election_officials",53,("state_results","pdf","csv")),
    "NM": StateExpansionProfile("NM","county","county","central_county_clerks",33,("clarity","scytl","unknown_web")),
    "NY": StateExpansionProfile("NY","county+board-of-elections","county_board","central_county_boards",62,("scytl","clarity","pdf")),
    "RI": StateExpansionProfile("RI","state+municipal","municipality","central_local_boards",39,("state_results","pdf","csv")),
    "SC": StateExpansionProfile("SC","county+state","county","central_county_election_offices",46,("scytl","clarity","unknown_web")),
    "VT": StateExpansionProfile("VT","town","town","central_town_clerks",247,("pdf","csv","unknown_web")),
    "WI": StateExpansionProfile("WI","municipal+county","municipality","central_clerk_directory",1850,("state_results","pdf","csv")),
}


def expansion_profile(state: str) -> StateExpansionProfile:
    key=state.strip().upper()
    if key not in PROFILES:
        raise KeyError(f"no expansion profile for {key}")
    return PROFILES[key]


def classify_result_family(url: str, text: str="") -> str:
    blob=(url+" "+text[:200000]).lower()
    host=(urlparse(url).hostname or "").lower()
    if "enhancedvoting" in blob:
        return "enhanced_voting"
    if "clarityelections" in blob or "election night reporting" in blob:
        return "clarity"
    if "scytl" in blob:
        return "scytl"
    if "electionware" in blob:
        return "electionware"
    if "civicplus" in blob or "civicengage" in blob or "documentcenter" in blob:
        return "civicplus"
    if any(token in blob for token in (".csv",".xlsx",".xls")):
        return "tabular_download"
    if ".pdf" in blob:
        return "pdf"
    if host.endswith(".gov") or ".gov." in host:
        return "official_web"
    return "unknown_web"
