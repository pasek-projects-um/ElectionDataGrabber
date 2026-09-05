from __future__ import annotations
import csv
from pathlib import Path

def summarize(path=Path("registry/pa_county_capabilities.csv")):
    with path.open(encoding="utf-8-sig") as f:
        rows=list(csv.DictReader(f))
    counts={}
    for r in rows:
        counts[r["portability_class"]]=counts.get(r["portability_class"],0)+1
    return {"counties":len(rows),**counts}

if __name__=="__main__":
    print(summarize())
