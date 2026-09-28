from __future__ import annotations

import csv
from collections import Counter
from pathlib import Path


def read_rows(path: Path) -> list[dict[str,str]]:
    with path.open(encoding="utf-8-sig",newline="") as f:
        return list(csv.DictReader(f))


def residual_class(row: dict[str,str]) -> str:
    failure=row.get("failure_class","")
    stage=row.get("execution_stage","")
    family=row.get("access_family","")
    if not failure and stage in {"normalized","replay_tested","refresh_verified"}:
        return "complete"
    if failure.startswith("http_") or failure in {"network_error","timeout","promotion_fetch_blocked"}:
        return "fetch_hardening"
    if failure in {"no_structured_artifact_discovered","requires_download_artifact_selection","artifact_discovered_requires_fetch"}:
        return "artifact_discovery"
    if failure in {"invalid_json_payload","no_normalized_observations"}:
        return "schema_adaptation"
    if failure in {"parser_not_executable","artifact_family_not_executable","needs_platform_work"}:
        return "new_platform_or_parser"
    if stage=="parser_selected":
        return "parser_followup"
    if family in {"clarity","structured_json","structured_xml","tabular_download"}:
        return "known_family_followup"
    return "unclassified_followup"


def summarize(rows: list[dict[str,str]]) -> list[dict[str,str]]:
    counts=Counter((residual_class(r),r.get("access_family","")) for r in rows)
    out=[]
    for (kind,family),count in sorted(counts.items(),key=lambda kv:(kv[0][0]!="complete",-kv[1],kv[0][0],kv[0][1])):
        out.append({
            "residual_class":kind,
            "access_family":family,
            "source_count":str(count),
            "priority":str(
                0 if kind=="complete" else
                5 if kind=="known_family_followup" else
                4 if kind in {"artifact_discovery","schema_adaptation"} else
                3 if kind=="fetch_hardening" else
                2
            ),
        })
    return sorted(out,key=lambda r:(-int(r["priority"]),-int(r["source_count"]),r["residual_class"],r["access_family"]))


def main() -> None:
    root=Path(__file__).resolve().parents[1]
    rows=read_rows(root/"audit/harvested_source_execution_results.csv")
    out=root/"audit/harvested_execution_residuals.csv"
    data=summarize(rows)
    fields=["residual_class","access_family","source_count","priority"]
    with out.open("w",encoding="utf-8",newline="") as f:
        w=csv.DictWriter(f,fieldnames=fields); w.writeheader(); w.writerows(data)


if __name__=="__main__":
    main()
