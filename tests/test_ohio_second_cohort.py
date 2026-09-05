from pathlib import Path
import csv

VERIFIED={"Ashtabula","Belmont","Clark","Darke","Erie","Fairfield","Fayette","Geauga","Knox"}

def test_second_cohort_verified_boe_family():
    with Path("registry/oh_county_capabilities.csv").open() as f:
        rows={r["county"]:r for r in csv.DictReader(f)}
    for county in VERIFIED:
        assert rows[county]["portability_class"] == "A"
        assert rows[county]["precinct_level"] == "true"
        assert "BOE" in rows[county]["platform_or_shape"]
