from __future__ import annotations

import csv
from collections import Counter
from pathlib import Path


def prioritize(expansion_path: Path, census_path: Path) -> list[dict[str,str]]:
    expansion=list(csv.DictReader(expansion_path.open(encoding="utf-8")))
    census={r["state"]:r for r in csv.DictReader(census_path.open(encoding="utf-8"))}
    out=[]
    states=sorted(set(census)|{r["state"] for r in expansion})
    for state in states:
        erows=[r for r in expansion if r["state"]==state]
        reached=sum(r["status"]=="reached" for r in erows)
        result_links=sum(bool(r["result_links"]) for r in erows)
        live=sum(r["election_night_candidate"].lower()=="true" for r in erows)
        fam=Counter(r["platform_family"] or "unclassified" for r in erows)
        c=census.get(state,{})
        expected=int(c.get("expected_primary_units") or 0)
        enumerated=int(c.get("enumerated_primary_units") or 0)
        if enumerated:
            phase="canonicalized"
        elif reached and result_links:
            phase="promote_discovered_sources"
        elif reached:
            phase="classify_reached_authorities"
        else:
            phase="resolve_central_directory"
        out.append({
            "state":state,
            "phase":phase,
            "expected_primary_units":str(expected),
            "canonical_units":str(enumerated),
            "discovered_rows":str(len(erows)),
            "reached_authorities":str(reached),
            "rows_with_result_links":str(result_links),
            "election_night_candidates":str(live),
            "discovered_families":"|".join(f"{k}:{v}" for k,v in fam.most_common()),
        })
    return out


def write(rows: list[dict[str,str]], path: Path) -> None:
    path.parent.mkdir(parents=True,exist_ok=True)
    fields=list(rows[0]) if rows else []
    with path.open("w",newline="",encoding="utf-8") as f:
        w=csv.DictWriter(f,fieldnames=fields); w.writeheader(); w.writerows(rows)


if __name__=="__main__":
    root=Path(__file__).resolve().parents[1]
    rows=prioritize(root/"audit/us-state-central-authority-expansion.csv",root/"audit/state_unit_data_access_census.csv")
    write(rows,root/"audit/state_coverage_gap_priorities.csv")
