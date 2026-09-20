from __future__ import annotations

import csv
from pathlib import Path

STATE_COUNTS={"IA":99,"MD":24,"OR":36,"VA":133}
TARGET_STATES=set(STATE_COUNTS)


def promotable_rows(expansion_path: Path) -> list[dict[str,str]]:
    rows=list(csv.DictReader(expansion_path.open(encoding="utf-8")))
    out=[]; seen=set()
    for r in rows:
        if r["state"] not in TARGET_STATES or r["status"]!="reached":
            continue
        url=(r.get("authority_url") or "").strip()
        host=(r.get("authority_host") or "").strip().lower()
        if not url or not host:
            continue
        key=(r["state"],url)
        if key in seen: continue
        seen.add(key)
        out.append({
            "state":r["state"],
            "authority_url":url,
            "authority_host":host,
            "result_links":(r.get("result_links") or "").strip(),
            "election_night_candidate":r.get("election_night_candidate",""),
            "smallest_observed_unit":r.get("smallest_observed_unit",""),
            "platform_family":r.get("platform_family",""),
        })
    return out


def summarize(rows: list[dict[str,str]]) -> list[dict[str,str]]:
    out=[]
    for state in sorted(STATE_COUNTS):
        sr=[r for r in rows if r["state"]==state]
        out.append({
            "state":state,
            "expected_primary_units":str(STATE_COUNTS[state]),
            "reached_surfaces":str(len(sr)),
            "surfaces_with_result_links":str(sum(bool(r["result_links"]) for r in sr)),
            "election_night_candidates":str(sum(r["election_night_candidate"].lower()=="true" for r in sr)),
            "precinct_or_finer_surfaces":str(sum((r["smallest_observed_unit"] or "") in {"precinct","ward","district"} for r in sr)),
        })
    return out


def write(rows: list[dict[str,str]], path: Path) -> None:
    path.parent.mkdir(parents=True,exist_ok=True)
    fields=list(rows[0]) if rows else []
    with path.open("w",newline="",encoding="utf-8") as f:
        w=csv.DictWriter(f,fieldnames=fields); w.writeheader(); w.writerows(rows)


if __name__=="__main__":
    root=Path(__file__).resolve().parents[1]
    rows=promotable_rows(root/"audit/us-state-central-authority-expansion.csv")
    write(rows,root/"audit/ia_md_or_va_promotable_surfaces.csv")
    write(summarize(rows),root/"audit/ia_md_or_va_promotion_summary.csv")
