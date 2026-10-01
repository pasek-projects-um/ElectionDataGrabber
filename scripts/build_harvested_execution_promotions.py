from __future__ import annotations

import csv
from pathlib import Path

from election_data_grabber.readiness_adapter_bridge import readiness_route
from election_data_grabber.supported_execution import PARSER_FUNCTIONS


DISCOVERY_ROUTES={
    "election_data_grabber.adapters.clarity:discover_clarity_downloads",
    "election_data_grabber.adapters.vendor_structured:discover_vendor_artifacts",
}


def read_rows(path: Path) -> list[dict[str,str]]:
    with path.open(encoding="utf-8-sig",newline="") as f:
        return list(csv.DictReader(f))


def promotion_action(row: dict[str,str]) -> tuple[str,str,str]:
    if row.get("fetch_status")!="fetchable":
        return row.get("platform_family",""),"","fetch_blocked"
    family,route=readiness_route(row)
    if route in PARSER_FUNCTIONS:
        return family,route,"execute_now"
    if route in DISCOVERY_ROUTES:
        return family,route,"discover_artifact"
    return family,route,"needs_platform_work"


def build_promotions(rows: list[dict[str,str]]) -> list[dict[str,str]]:
    out=[]
    for row in rows:
        family,route,action=promotion_action(row)
        out.append({
            **row,
            "promoted_family":family,
            "execution_route":route,
            "promotion_action":action,
        })
    return out


def main() -> None:
    root=Path(__file__).resolve().parents[1]
    inp=root/"audit/harvested_source_probe.csv"
    rows=read_rows(inp) if inp.exists() else []
    out=root/"audit/harvested_source_execution_promotions.csv"
    fields=[
        "state","source_url","source_origin","fetch_status","http_status",
        "platform_family","confidence","evidence","discovered_artifacts",
        "promoted_family","execution_route","promotion_action",
    ]
    with out.open("w",encoding="utf-8",newline="") as f:
        w=csv.DictWriter(f,fieldnames=fields); w.writeheader()
        for row in build_promotions(rows):
            w.writerow({k:row.get(k,"") for k in fields})


if __name__=="__main__":
    main()
