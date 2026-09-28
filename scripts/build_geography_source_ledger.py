from __future__ import annotations

import csv
from pathlib import Path


def read_rows(path: Path) -> list[dict[str,str]]:
    with path.open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def build_geography_ledger(localities: list[dict[str,str]]) -> list[dict[str,str]]:
    out=[]
    for r in localities:
        final=bool(r.get("final_evidence_url"))
        live=bool(r.get("election_night_evidence_url"))
        out.append({
            "jurisdiction_id":r["jurisdiction_id"],
            "authority_id":r.get("authority_id",""),
            "state":r["state"],
            "jurisdiction_level":r["jurisdiction_level"],
            "canonical_name":r["canonical_name"],
            "coverage_status":r["coverage_status"],
            "final_evidence_url":r.get("final_evidence_url",""),
            "election_night_evidence_url":r.get("election_night_evidence_url",""),
            "has_any_source":"true" if final or live else "false",
            "search_status":"resolved" if final or live else "unresolved",
            "search_query":f'{r["canonical_name"]} {r["state"]} election results',
        })
    return sorted(out,key=lambda r:(r["state"],r["jurisdiction_level"],r["canonical_name"]))


def unresolved_queue(rows: list[dict[str,str]]) -> list[dict[str,str]]:
    return [r for r in rows if r["search_status"]=="unresolved"]


def main() -> None:
    root=Path(__file__).resolve().parents[1]
    localities=read_rows(root/"registry/us_primary_election_localities.csv")
    ledger=build_geography_ledger(localities)
    outputs={
        root/"audit/geography_source_evidence_ledger.csv":ledger,
        root/"audit/geography_unresolved_search_queue.csv":unresolved_queue(ledger),
    }
    for path,rows in outputs.items():
        path.parent.mkdir(parents=True,exist_ok=True)
        fields=list(ledger[0].keys())
        with path.open("w",encoding="utf-8",newline="") as f:
            w=csv.DictWriter(f,fieldnames=fields); w.writeheader(); w.writerows(rows)


if __name__=="__main__":
    main()
