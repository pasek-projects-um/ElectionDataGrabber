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
            "source_count":str(int(final)+int(live)),
            "has_any_source":"true" if final or live else "false",
            "search_status":"resolved" if final or live else "unresolved",
            "search_query":f'{r["canonical_name"]} {r["state"]} election results',
        })
    return sorted(out,key=lambda r:(r["state"],r["jurisdiction_level"],r["canonical_name"]))


def build_source_leads(localities: list[dict[str,str]]) -> list[dict[str,str]]:
    leads=[]
    seen=set()
    def add(r: dict[str,str], url: str, role: str) -> None:
        if not url:
            return
        key=(r["jurisdiction_id"],url,role)
        if key in seen:
            return
        seen.add(key)
        leads.append({
            "jurisdiction_id":r["jurisdiction_id"],
            "authority_id":r.get("authority_id",""),
            "state":r["state"],
            "canonical_name":r["canonical_name"],
            "lead_url":url,
            "source_role":role,
            "lead_origin":"existing_capability_registry",
            "official_status":"official_or_presumed_official",
            "execution_stage":"discovered",
        })
    for r in localities:
        add(r,r.get("final_evidence_url",""),"final")
        add(r,r.get("election_night_evidence_url",""),"election_night")
    return sorted(leads,key=lambda r:(r["state"],r["canonical_name"],r["source_role"],r["lead_url"]))


def unresolved_queue(rows: list[dict[str,str]]) -> list[dict[str,str]]:
    return [r for r in rows if r["search_status"]=="unresolved"]


def main() -> None:
    root=Path(__file__).resolve().parents[1]
    localities=read_rows(root/"registry/us_primary_election_localities.csv")
    ledger=build_geography_ledger(localities)
    leads=build_source_leads(localities)
    outputs={
        root/"audit/geography_source_evidence_ledger.csv":ledger,
        root/"audit/geography_unresolved_search_queue.csv":unresolved_queue(ledger),
        root/"audit/geography_source_leads.csv":leads,
    }
    for path,rows in outputs.items():
        path.parent.mkdir(parents=True,exist_ok=True)
        fields=list(rows[0].keys()) if rows else (list(ledger[0].keys()) if "source_leads" not in path.name else ["jurisdiction_id","authority_id","state","canonical_name","lead_url","source_role","lead_origin","official_status","execution_stage"])
        with path.open("w",encoding="utf-8",newline="") as f:
            w=csv.DictWriter(f,fieldnames=fields); w.writeheader(); w.writerows(rows)


if __name__=="__main__":
    main()
