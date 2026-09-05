from __future__ import annotations
import csv
from pathlib import Path
TRACKER=Path("registry/us_local_unit_coverage_tracker.csv")
DISCOVERY=Path("audit/us-state-central-authority-expansion.csv")
def main():
    if not DISCOVERY.exists():
        print("no discovery artifact; tracker unchanged"); return
    with TRACKER.open(encoding="utf-8-sig") as f: rows=list(csv.DictReader(f))
    with DISCOVERY.open(encoding="utf-8-sig") as f: obs=list(csv.DictReader(f))
    by={}
    for r in obs:
        if r.get("status")=="reached": by.setdefault(r["state"],set()).add(r["authority_url"])
    for r in rows:
        expected=int(r["expected_primary_units"] or 0)
        known=min(expected,len(by.get(r["state"],set())))
        missing=int(r["known_units_missing_source"] or 0)
        r["known_units_with_source"]=str(known)
        r["estimated_unknown_units"]=str(max(0,expected-known-missing))
        if known: r["status"]="observed"
    with TRACKER.open("w",newline="",encoding="utf-8") as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
    print("COVERAGE",sum(int(r["known_units_with_source"]) for r in rows),"/",sum(int(r["expected_primary_units"]) for r in rows))
if __name__=="__main__": main()
