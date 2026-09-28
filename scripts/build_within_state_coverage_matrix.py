from __future__ import annotations

import csv
from collections import defaultdict
from pathlib import Path

STAGES=("discovered","fetchable","parser_selected","parse_executed","normalized","replay_tested","refresh_verified")


def read_rows(path: Path) -> list[dict[str,str]]:
    with path.open(encoding="utf-8-sig",newline="") as f:
        return list(csv.DictReader(f))


def highest_stage(rows: list[dict[str,str]]) -> str:
    stages={r.get("stage","").lower() for r in rows}
    return next((s for s in reversed(STAGES) if s in stages),"discovered")


def build_matrix(
    first_pass: list[dict[str,str]],
    denominators: list[dict[str,str]],
    localities: list[dict[str,str]],
    leads: list[dict[str,str]],
    execution: list[dict[str,str]],
) -> list[dict[str,str]]:
    denom={r["state"]:r for r in denominators}
    by_state_localities=defaultdict(list)
    by_state_leads=defaultdict(list)
    by_state_exec=defaultdict(list)
    for r in localities:
        by_state_localities[r.get("state","")].append(r)
    for r in leads:
        by_state_leads[r.get("state","")].append(r)
    for r in execution:
        by_state_exec[r.get("state","")].append(r)

    out=[]
    for surface in first_pass:
        state=surface["state"]
        d=denom.get(state,{})
        loc=by_state_localities[state]
        state_leads=by_state_leads[state]
        ex=by_state_exec[state]
        expected=int(d.get("expected_primary_units") or 0)
        enumerated=len({r["jurisdiction_id"] for r in loc if r.get("jurisdiction_id")})
        units_with_lead=len({r["jurisdiction_id"] for r in state_leads if r.get("jurisdiction_id")})
        executable=sum(1 for r in ex if r.get("stage","").lower() in {"parser_selected","parse_executed","normalized","replay_tested","refresh_verified"})
        normalized=sum(1 for r in ex if r.get("stage","").lower() in {"normalized","replay_tested","refresh_verified"})
        replay=sum(1 for r in ex if r.get("stage","").lower() in {"replay_tested","refresh_verified"})
        refresh=sum(1 for r in ex if r.get("stage","").lower()=="refresh_verified")
        election_night=surface.get("election_night_candidate","").lower()=="true"
        reasons=[]
        if expected and enumerated<expected:
            reasons.append("enumeration_gap")
        if enumerated and units_with_lead<enumerated:
            reasons.append("source_lead_gap")
        if not ex:
            reasons.append("no_execution_evidence")
        if normalized==0:
            reasons.append("no_normalized_execution")
        if election_night and refresh==0:
            reasons.append("election_night_refresh_unverified")
        priority=(3 if election_night else 0)+(2 if expected and enumerated<expected else 0)+(2 if enumerated and units_with_lead<enumerated else 0)+(2 if normalized==0 else 0)
        out.append({
            "state":state,
            "first_pass_result_url":surface.get("result_url",""),
            "source_scope":surface.get("source_scope",""),
            "election_night_candidate":surface.get("election_night_candidate",""),
            "authority_model":d.get("authority_model","unknown"),
            "expected_primary_units":str(expected) if expected else "",
            "enumerated_primary_units":str(enumerated),
            "units_with_any_lead":str(units_with_lead),
            "enumeration_ratio":f"{enumerated/expected:.4f}" if expected else "",
            "lead_coverage_ratio":f"{units_with_lead/enumerated:.4f}" if enumerated else "",
            "catalogued_source_leads":str(len(state_leads)),
            "execution_rows":str(len(ex)),
            "highest_execution_stage":highest_stage(ex),
            "executable_sources":str(executable),
            "normalized_sources":str(normalized),
            "replay_tested_sources":str(replay),
            "refresh_verified_sources":str(refresh),
            "depth_priority":str(priority),
            "depth_reasons":";".join(reasons) or "baseline_satisfied",
        })
    return sorted(out,key=lambda r:r["state"])


def build_priority_queue(matrix: list[dict[str,str]]) -> list[dict[str,str]]:
    return sorted(matrix,key=lambda r:(-int(r["depth_priority"]),r["state"]))


def main() -> None:
    root=Path(__file__).resolve().parents[1]
    first_pass=read_rows(root/"registry/first_pass_state_result_surfaces.csv")
    denominators=read_rows(root/"registry/us_primary_election_locality_denominators.csv")
    localities=read_rows(root/"registry/us_primary_election_localities.csv")
    leads_path=root/"audit/geography_source_leads.csv"
    execution_path=root/"audit/national_supported_execution.csv"
    leads=read_rows(leads_path) if leads_path.exists() else []
    execution=read_rows(execution_path) if execution_path.exists() else []
    rows=build_matrix(first_pass,denominators,localities,leads,execution)
    outputs={
        root/"audit/national_within_state_coverage_matrix.csv":rows,
        root/"audit/national_within_state_depth_priority.csv":build_priority_queue(rows),
    }
    for out,data in outputs.items():
        out.parent.mkdir(parents=True,exist_ok=True)
        with out.open("w",encoding="utf-8",newline="") as f:
            w=csv.DictWriter(f,fieldnames=list(data[0].keys())); w.writeheader(); w.writerows(data)


if __name__=="__main__":
    main()
