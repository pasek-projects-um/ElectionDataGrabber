import csv
from pathlib import Path

def _rows(path):
    with Path(path).open(encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))

def test_connecticut_registry_covers_all_169_unique_towns():
    authorities=_rows("registry/ct_town_authorities.csv")
    capabilities=_rows("registry/ct_town_capabilities.csv")
    a={r["locality"] for r in authorities}
    c={r["locality"] for r in capabilities}
    assert len(authorities) == 169
    assert len(a) == 169
    assert len(capabilities) == 169
    assert len(c) == 169
    assert a == c
