from __future__ import annotations

import csv
from pathlib import Path


def read_rows(path: Path) -> list[dict[str,str]]:
    with path.open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def by_state(rows: list[dict[str,str]]) -> dict[str,dict[str,str]]:
    return {r["state"]: r for r in rows}


def build_gap_matrix(root: Path) -> list[dict[str,str]]:
    elect=by_state(read_rows(root/"audit/electproject_2020_coverage_status.csv"))
    medsl=by_state(read_rows(root/"audit/medsl_2024_source_leads.csv"))
    nyt=by_state(read_rows(root/"audit/nyt_2024_state_source_coverage.csv"))
    down=by_state(read_rows(root/"audit/downballotr_official_source_leads.csv"))
    first_pass=by_state(read_rows(root/"registry/first_pass_state_result_surfaces.csv"))
    states=sorted(elect)
    out=[]
    for st in states:
        e=elect[st]; m=medsl[st]; n=nyt[st]; d=down.get(st)
        official_candidates=0
        if e["harvest_status"] in {"direct_official_url","official_social_reference","official_file_share","official_dashboard_candidate"}:
            official_candidates += max(1,int(e["lead_count"] or 0))
        if m["source_class"]=="official_candidate":
            official_candidates += 1
        if n["source_class"]=="official_candidate":
            official_candidates += 1
        if d:
            official_candidates += 1
        internal=first_pass.get(st)
        if internal and internal.get("result_url"):
            official_candidates += 1
        secondary_only=(official_candidates==0 and any([
            e["harvest_status"] in {"secondary_source","secondary_or_manual_collection","local_official_sources_aggregate","derived_local_dataset_no_source_pointer"},
            m["source_class"]!="official_candidate",
            n["source_class"] in {"secondary_repository","secondary_source"},
        ]))
        reasons=[]
        if not e["source_url"]:
            reasons.append("electproject_no_url")
        if m["source_class"]!="official_candidate":
            reasons.append("medsl_nonprimary")
        if n["source_class"]=="no_direct_source_link":
            reasons.append("nyt_no_direct_link")
        elif n["source_class"] in {"secondary_repository","secondary_source"}:
            reasons.append("nyt_secondary")
        if not d:
            reasons.append("no_downballotr_live_scraper")
        if secondary_only:
            reasons.append("secondary_only")
        priority=(3 if official_candidates==0 else 0)+(2 if secondary_only else 0)+(1 if "electproject_no_url" in reasons else 0)+(1 if "nyt_no_direct_link" in reasons else 0)
        out.append({
            "state":st,
            "official_candidate_count":str(official_candidates),
            "electproject_status":e["harvest_status"],
            "medsl_source_class":m["source_class"],
            "nyt_source_class":n["source_class"],
            "downballotr_live":"true" if d else "false",
            "internal_first_pass_url":internal.get("result_url","") if internal else "",
            "secondary_only":"true" if secondary_only else "false",
            "gap_priority":str(priority),
            "gap_reasons":";".join(reasons) or "none",
        })
    return sorted(out,key=lambda r:(-int(r["gap_priority"]),r["state"]))


def main() -> None:
    root=Path(__file__).resolve().parents[1]
    rows=build_gap_matrix(root)
    out=root/"audit/external_corpus_gap_matrix.csv"
    with out.open("w",encoding="utf-8",newline="") as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0].keys()))
        w.writeheader(); w.writerows(rows)


if __name__=="__main__":
    main()
