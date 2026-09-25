from __future__ import annotations

PARSER_BY_FAMILY = {
    "enhanced_voting": "election_data_grabber.adapters.enhanced_voting:parse_enhanced_voting_html",
    "clarity": "election_data_grabber.adapters.clarity:discover_clarity_downloads",
    "tabular_download": "election_data_grabber.adapters.generic_csv:parse_generic_precinct_csv",
}

def supported_ingest_manifest(candidates: list[dict[str, str]]) -> list[dict[str, str]]:
    """Return only candidates the current code can actually process without a new adapter."""
    out=[]
    for row in candidates:
        if row.get("ingest_tier") != "ready_adapter":
            continue
        family=row["access_family"]
        parser=PARSER_BY_FAMILY.get(family)
        if family == "tabular_download":
            lower = row["result_url"].lower()
            if lower.endswith(".xls") or ".xls?" in lower or lower.endswith(".xlsx") or ".xlsx?" in lower:
                parser = "election_data_grabber.adapters.generic_excel:parse_generic_precinct_excel"
        if not parser:
            continue
        out.append({
            "state":row["state"],
            "result_url":row["result_url"],
            "access_family":family,
            "parser":parser,
            "smallest_observed_unit":row.get("smallest_observed_unit","unknown"),
            "status":"supported_unverified",
        })
    return sorted(out,key=lambda r:(r["access_family"],r["state"],r["result_url"]))
