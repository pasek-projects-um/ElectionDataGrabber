from __future__ import annotations

import csv
from collections import Counter, defaultdict
from pathlib import Path


STAGES=("discovered","fetchable","parser_selected","parse_executed","normalized","replay_tested","refresh_verified")


def read_rows(path: Path) -> list[dict[str,str]]:
    with path.open(encoding="utf-8-sig",newline="") as f:
        return list(csv.DictReader(f))


def summarize(rows: list[dict[str,str]]) -> list[dict[str,str]]:
    by_state=defaultdict(list)
    for row in rows:
        by_state[row.get("state","")].append(row)
    out=[]
    for state,state_rows in sorted(by_state.items()):
        counts=Counter(r.get("execution_stage","") for r in state_rows)
        highest=next((s for s in reversed(STAGES) if counts[s]),"discovered")
        out.append({
            "state":state,
            "sources_attempted":str(len(state_rows)),
            "fetch_or_execution_failures":str(sum(1 for r in state_rows if r.get("failure_class"))),
            "parser_selected_or_higher":str(sum(counts[s] for s in STAGES[2:])),
            "normalized_or_higher":str(sum(counts[s] for s in STAGES[4:])),
            "replay_tested_or_higher":str(sum(counts[s] for s in STAGES[5:])),
            "refresh_verified":str(counts["refresh_verified"]),
            "highest_execution_stage":highest,
        })
    return out


def main() -> None:
    root=Path(__file__).resolve().parents[1]
    path=root/"audit/harvested_source_execution_results.csv"
    rows=read_rows(path) if path.exists() else []
    summary=summarize(rows)
    out=root/"audit/harvested_execution_depth_summary.csv"
    fields=[
        "state","sources_attempted","fetch_or_execution_failures",
        "parser_selected_or_higher","normalized_or_higher",
        "replay_tested_or_higher","refresh_verified","highest_execution_stage",
    ]
    with out.open("w",encoding="utf-8",newline="") as f:
        w=csv.DictWriter(f,fieldnames=fields); w.writeheader(); w.writerows(summary)


if __name__=="__main__":
    main()
