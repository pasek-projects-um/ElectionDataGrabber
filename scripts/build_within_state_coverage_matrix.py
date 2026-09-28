from __future__ import annotations

import csv
from collections import defaultdict
from pathlib import Path

STAGES = ("discovered","fetchable","parser_selected","parse_executed","normalized","replay_tested","refresh_verified")

def read_rows(path: Path) -> list[dict[str,str]]:
    with path.open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))

def build_matrix(first_pass: list[dict[str,str]], candidates: list[dict[str,str]], execution: list[dict[str,str]]) -> list[dict[str,str]]:
    by_state_candidates=defaultdict(list)
    for row in candidates:
        by_state_candidates[row.get("state","")].append(row)
    by_state_exec=defaultdict(list)
    for row in execution:
        by_state_exec[row.get("state","")].append(row)
    out=[]
    for row in first_pass:
        state=row["state"]
        cand=by_state_candidates[state]
        ex=by_state_exec[state]
        stages={e.get("stage","").lower() for e in ex}
        highest=""
        for stage in STAGES:
            if stage in stages:
                highest=stage
        out.append({
            "state":state,
            "first_pass_result_url":row["result_url"],
            "source_scope":row["source_scope"],
            "election_night_candidate":row["election_night_candidate"],
            "smallest_observed_unit":row["smallest_observed_unit"],
            "catalogued_result_urls":str(len(cand)),
            "catalogued_hosts":str(len({r.get("result_host","") for r in cand if r.get("result_host")})),
            "execution_rows":str(len(ex)),
            "highest_execution_stage":highest or "discovered",
            "normalized_sources":str(sum(1 for e in ex if e.get("stage","").lower() in {"normalized","replay_tested","refresh_verified"})),
            "needs_within_state_depth":"true" if row["source_scope"] != "statewide" or len(cand) <= 1 else "false",
        })
    return sorted(out,key=lambda r:r["state"])

def main() -> None:
    root=Path(__file__).resolve().parents[1]
    first_pass=read_rows(root/"registry/first_pass_state_result_surfaces.csv")
    candidates_path=root/"audit/national_easy_ingest_candidates.csv"
    execution_path=root/"audit/national_supported_execution.csv"
    candidates=read_rows(candidates_path) if candidates_path.exists() else []
    execution=read_rows(execution_path) if execution_path.exists() else []
    rows=build_matrix(first_pass,candidates,execution)
    out=root/"audit/national_within_state_coverage_matrix.csv"
    out.parent.mkdir(parents=True,exist_ok=True)
    fields=list(rows[0].keys())
    with out.open("w",encoding="utf-8",newline="") as f:
        w=csv.DictWriter(f,fieldnames=fields); w.writeheader(); w.writerows(rows)

if __name__=="__main__":
    main()
