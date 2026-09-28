from __future__ import annotations

import csv
from collections import defaultdict
from pathlib import Path

STAGES = ("discovered","fetchable","parser_selected","parse_executed","normalized","replay_tested","refresh_verified")

def read_rows(path: Path) -> list[dict[str,str]]:
    with path.open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))

def profile_map(rows: list[dict[str,str]]) -> dict[str,dict[str,str]]:
    return {r["state"]: r for r in rows if r.get("state")}

def build_matrix(first_pass: list[dict[str,str]], candidates: list[dict[str,str]], execution: list[dict[str,str]], profiles: list[dict[str,str]] | None=None) -> list[dict[str,str]]:
    profiles_by_state=profile_map(profiles or [])
    by_state_candidates=defaultdict(list)
    for row in candidates:
        by_state_candidates[row.get("state","")].append(row)
    by_state_exec=defaultdict(list)
    for row in execution:
        by_state_exec[row.get("state","")].append(row)
    out=[]
    for row in first_pass:
        state=row["state"]; cand=by_state_candidates[state]; ex=by_state_exec[state]
        profile=profiles_by_state.get(state,{})
        stages={e.get("stage","").lower() for e in ex}
        highest=next((s for s in reversed(STAGES) if s in stages),"discovered")
        expected=int(profile.get("expected_units") or 0)
        observed_units=len({r.get("jurisdiction_id") or r.get("authority_id") or r.get("result_url") for r in cand if r.get("jurisdiction_id") or r.get("authority_id") or r.get("result_url")})
        depth_ratio=(observed_units/expected) if expected else None
        normalized=sum(1 for e in ex if e.get("stage","").lower() in {"normalized","replay_tested","refresh_verified"})
        election_night=row["election_night_candidate"].lower()=="true"
        reasons=[]
        if row["source_scope"]!="statewide": reasons.append("no_statewide_surface")
        if expected and observed_units<expected: reasons.append("jurisdiction_gap")
        if not cand: reasons.append("not_in_generated_candidate_inventory")
        if normalized==0: reasons.append("no_normalized_execution")
        if election_night and highest!="refresh_verified": reasons.append("election_night_refresh_unverified")
        priority=(3 if election_night else 0)+(2 if row["source_scope"]!="statewide" else 0)+(2 if expected and observed_units<expected else 0)+(2 if normalized==0 else 0)+(1 if not cand else 0)
        out.append({
            "state":state,
            "first_pass_result_url":row["result_url"],
            "source_scope":row["source_scope"],
            "election_night_candidate":row["election_night_candidate"],
            "smallest_observed_unit":row["smallest_observed_unit"],
            "authority_model":profile.get("profile_type","unknown"),
            "expected_units":str(expected) if expected else "",
            "observed_catalog_units":str(observed_units),
            "catalog_depth_ratio":f"{depth_ratio:.4f}" if depth_ratio is not None else "",
            "catalogued_result_urls":str(len(cand)),
            "catalogued_hosts":str(len({r.get("result_host","") for r in cand if r.get("result_host")})),
            "execution_rows":str(len(ex)),
            "highest_execution_stage":highest,
            "normalized_sources":str(normalized),
            "depth_priority":str(priority),
            "depth_reasons":";".join(reasons) or "baseline_satisfied",
        })
    return sorted(out,key=lambda r:r["state"])

def build_priority_queue(matrix: list[dict[str,str]]) -> list[dict[str,str]]:
    return sorted(matrix,key=lambda r:(-int(r["depth_priority"]), r["state"]))

def main() -> None:
    root=Path(__file__).resolve().parents[1]
    first_pass=read_rows(root/"registry/first_pass_state_result_surfaces.csv")
    profiles=read_rows(root/"registry/us_state_directory_profiles.csv")
    candidates_path=root/"audit/national_easy_ingest_candidates.csv"
    execution_path=root/"audit/national_supported_execution.csv"
    candidates=read_rows(candidates_path) if candidates_path.exists() else []
    execution=read_rows(execution_path) if execution_path.exists() else []
    rows=build_matrix(first_pass,candidates,execution,profiles)
    outputs={
        root/"audit/national_within_state_coverage_matrix.csv": rows,
        root/"audit/national_within_state_depth_priority.csv": build_priority_queue(rows),
    }
    for out,data in outputs.items():
        out.parent.mkdir(parents=True,exist_ok=True)
        with out.open("w",encoding="utf-8",newline="") as f:
            w=csv.DictWriter(f,fieldnames=list(data[0].keys())); w.writeheader(); w.writerows(data)

if __name__=="__main__":
    main()
