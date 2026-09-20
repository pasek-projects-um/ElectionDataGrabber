import csv
from pathlib import Path

from scripts.prioritize_state_coverage_gaps import prioritize


def test_prioritizes_discovery_to_canonicalization_phases(tmp_path: Path):
    expansion=tmp_path/"exp.csv"
    expansion.write_text(
        "state,status,result_links,election_night_candidate,platform_family\n"
        "AZ,reached,https://x/results,true,clarity\n"
        "WI,central_fetch_failed:HTTPStatusError,,,\n",
        encoding="utf-8",
    )
    census=tmp_path/"census.csv"
    census.write_text(
        "state,expected_primary_units,enumerated_primary_units\n"
        "AZ,15,0\n"
        "MI,83,83\n"
        "WI,1850,0\n",
        encoding="utf-8",
    )
    rows={r["state"]:r for r in prioritize(expansion,census)}
    assert rows["AZ"]["phase"]=="promote_discovered_sources"
    assert rows["MI"]["phase"]=="canonicalized"
    assert rows["WI"]["phase"]=="resolve_central_directory"
    assert rows["AZ"]["election_night_candidates"]=="1"
