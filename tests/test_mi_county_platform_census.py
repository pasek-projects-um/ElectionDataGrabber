import csv
from pathlib import Path

from scripts.mi_county_platform_census import load_authorities, load_counties


def test_michigan_authority_registry_has_all_83_counties():
    authorities = load_authorities(Path("registry/mi_county_authorities.csv"))
    assert len(authorities) == 83
    assert all(url.startswith("http") for url in authorities.values())


def test_census_falls_back_to_authority_registry_when_county_file_missing(tmp_path):
    authorities = load_authorities(Path("registry/mi_county_authorities.csv"))
    counties = load_counties(tmp_path / "missing.csv", authorities)
    assert len(counties) == 83
    assert {row["county"] for row in counties} == set(authorities)


def test_capability_matrix_has_all_83_counties():
    with Path("registry/mi_county_capabilities.csv").open(encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))
    assert len(rows) == 83
    assert len({row["county"] for row in rows}) == 83
