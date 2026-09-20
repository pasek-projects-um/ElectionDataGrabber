from __future__ import annotations

import csv
from pathlib import Path

from election_data_grabber.easy_ingest import build_candidates, read_csv, summarize
from election_data_grabber.locality_registry import read_denominators\nfrom election_data_grabber.supported_ingest import supported_ingest_manifest

FIELDS=["state","authority_url","result_url","result_host","access_family","ingest_tier","election_night_candidate","smallest_observed_unit"]
SUMMARY_FIELDS=["ingest_tier","access_family","unique_result_urls","states","state_count","expected_units_exposed"]\nMANIFEST_FIELDS=["state","result_url","access_family","parser","smallest_observed_unit","status"]

def write_rows(path: Path, rows: list[dict[str,str]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open("w",encoding="utf-8",newline="") as f:
        w=csv.DictWriter(f,fieldnames=fields); w.writeheader(); w.writerows(rows)

def main() -> None:
    root=Path(__file__).resolve().parents[1]
    expansion=read_csv(root/"audit/us-state-central-authority-expansion.csv")
    den={d.state:d.expected_primary_units for d in read_denominators(root/"registry/us_primary_election_locality_denominators.csv")}
    candidates=build_candidates(expansion)
    write_rows(root/"audit/national_easy_ingest_candidates.csv",candidates,FIELDS)
    write_rows(root/"audit/national_easy_ingest_summary.csv",summarize(candidates,den),SUMMARY_FIELDS)\n    write_rows(root/"audit/national_supported_ingest_manifest.csv",supported_ingest_manifest(candidates),MANIFEST_FIELDS)

if __name__=="__main__":
    main()
