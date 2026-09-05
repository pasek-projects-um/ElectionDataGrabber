from __future__ import annotations
import csv
from pathlib import Path

REQUIRED=("state","locality_type","locality_name","authority_url","results_url","source_scope","election_night_candidate","smallest_observed_unit","platform_family","status","discovered_from")

def validate(path="registry/us_local_reporting_sources.csv"):
    with Path(path).open(encoding="utf-8-sig") as f:
        r=csv.DictReader(f)
        missing=set(REQUIRED)-set(r.fieldnames or [])
        if missing: raise SystemExit(f"missing columns: {sorted(missing)}")
        rows=list(r)
    print(f"validated {len(rows)} national source rows")

if __name__=="__main__": validate()
