from __future__ import annotations
import argparse, csv
from pathlib import Path
from election_data_grabber.locality_registry import derive_tracker, read_denominators, read_localities

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--localities",type=Path,default=Path("registry/us_primary_election_localities.csv"))
    ap.add_argument("--denominators",type=Path,default=Path("registry/us_primary_election_locality_denominators.csv"))
    ap.add_argument("--out",type=Path,default=Path("registry/us_local_unit_coverage_tracker.csv"))
    args=ap.parse_args()
    rows=derive_tracker(read_localities(args.localities),read_denominators(args.denominators))
    fields=list(rows[0]) if rows else []
    with args.out.open("w",newline="",encoding="utf-8") as f:
        w=csv.DictWriter(f,fieldnames=fields); w.writeheader(); w.writerows(rows)

if __name__=="__main__": main()
