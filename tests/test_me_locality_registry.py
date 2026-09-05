import csv
from pathlib import Path


def _rows(path):
    with Path(path).open(encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def test_maine_registry_has_60_unique_matching_localities():
    authorities=_rows("registry/me_locality_authorities.csv")
    capabilities=_rows("registry/me_locality_capabilities.csv")
    a={r["locality"] for r in authorities}
    c={r["locality"] for r in capabilities}
    assert len(authorities) == 60
    assert len(a) == 60
    assert len(capabilities) == 60
    assert len(c) == 60
    assert a == c
