from __future__ import annotations

import csv
from collections import Counter
from pathlib import Path


def read_rows(path: Path) -> list[dict[str,str]]:
    with path.open(encoding="utf-8-sig",newline="") as f:
        return list(csv.DictReader(f))


def next_action(row: dict[str,str]) -> str:
    status=row.get("fetch_status","")
    family=row.get("platform_family","")
    artifacts=row.get("discovered_artifacts","")
    if status != "fetchable":
        return "fetch_blocked"
    if family in {"clarity","enhanced_voting"}:
        return "execute_existing_adapter"
    if artifacts:
        return "artifact_discovery"
    if family in {"structured_web","scytl","electionware"}:
        return "new_platform_adapter"
    return "platform_probe_followup"


def build_readiness(rows: list[dict[str,str]]) -> list[dict[str,str]]:
    out=[]
    for row in rows:
        out.append({
            **row,
            "next_action":next_action(row),
        })
    return out


def build_summary(rows: list[dict[str,str]]) -> list[dict[str,str]]:
    counts=Counter(r["next_action"] for r in build_readiness(rows))
    return [{"next_action":k,"source_count":str(v)} for k,v in sorted(counts.items())]


def main() -> None:
    root=Path(__file__).resolve().parents[1]
    probe=read_rows(root/"audit/harvested_source_probe.csv")
    readiness=build_readiness(probe)
    out=root/"audit/harvested_source_readiness.csv"
    fields=list(readiness[0].keys())
    with out.open("w",encoding="utf-8",newline="") as f:
        w=csv.DictWriter(f,fieldnames=fields); w.writeheader(); w.writerows(readiness)
    summary=build_summary(probe)
    sout=root/"audit/harvested_source_readiness_summary.csv"
    with sout.open("w",encoding="utf-8",newline="") as f:
        w=csv.DictWriter(f,fieldnames=["next_action","source_count"]); w.writeheader(); w.writerows(summary)


if __name__=="__main__":
    main()
