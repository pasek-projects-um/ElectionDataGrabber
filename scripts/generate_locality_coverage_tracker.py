from __future__ import annotations
import argparse, csv
from pathlib import Path
from election_data_grabber.locality_registry import derive_tracker, read_denominators, read_localities
from election_data_grabber.source_capabilities import derived_capabilities, read_source_capabilities, validate_locality_bindings

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--localities",type=Path,default=Path("registry/us_primary_election_localities.csv"))
    ap.add_argument("--denominators",type=Path,default=Path("registry/us_primary_election_locality_denominators.csv"))
    ap.add_argument("--source-capabilities",type=Path,default=Path("registry/jurisdiction_source_capabilities.csv"))
    ap.add_argument("--out",type=Path,default=Path("registry/us_local_unit_coverage_tracker.csv"))
    args=ap.parse_args()
    localities=read_localities(args.localities)
    capabilities=read_source_capabilities(args.source_capabilities)
    validate_locality_bindings(capabilities,localities)
    rows=derive_tracker(
        localities,
        read_denominators(args.denominators),
        capability_map=derived_capabilities(capabilities),
    )
    fields=list(rows[0]) if rows else []
    with args.out.open("w",newline="",encoding="utf-8") as f:
        w=csv.DictWriter(f,fieldnames=fields); w.writeheader(); w.writerows(rows)

if __name__=="__main__": main()
