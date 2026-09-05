import csv
from pathlib import Path

def _names(path):
    with Path(path).open(encoding="utf-8-sig") as f:
        return [r["county"] for r in csv.DictReader(f)]

def test_ohio_registries_cover_all_88_unique_counties():
    authorities=_names("registry/oh_county_authorities.csv")
    capabilities=_names("registry/oh_county_capabilities.csv")
    assert len(authorities) == 88
    assert len(set(authorities)) == 88
    assert len(capabilities) == 88
    assert len(set(capabilities)) == 88
    assert set(authorities) == set(capabilities)
