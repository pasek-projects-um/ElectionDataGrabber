from __future__ import annotations

from election_data_grabber.adapters.structured_web import select_structured_artifact


def readiness_artifact(row: dict[str,str]):
    raw=row.get("discovered_artifacts","")
    urls=[u for u in raw.split("|") if u]
    return select_structured_artifact(urls)


def readiness_route(row: dict[str,str]) -> tuple[str,str]:
    family=row.get("platform_family","")
    artifact=readiness_artifact(row)
    if family=="clarity":
        return "clarity","election_data_grabber.adapters.clarity:discover_clarity_downloads"
    if family in {"scytl","electionware","results_portal","structured_web"} and artifact is None:
        return family,"election_data_grabber.adapters.vendor_structured:discover_vendor_artifacts"
    if artifact is not None:
        if artifact.kind=="json":
            return "structured_json","election_data_grabber.adapters.generic_json:parse_generic_results_json"
        if artifact.kind=="csv":
            return "tabular_download","election_data_grabber.adapters.generic_csv:parse_generic_precinct_csv"
        if artifact.kind=="xml":
            return "structured_xml","election_data_grabber.adapters.vendor_structured:discover_vendor_artifacts"
        if artifact.kind=="excel":
            return "tabular_download","election_data_grabber.adapters.generic_excel:parse_generic_precinct_excel"
    return family,""
