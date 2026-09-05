import csv
from pathlib import Path


def _rows(path):
    with Path(path).open(encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def test_maine_registry_has_unique_matching_localities():
    authorities=_rows("registry/me_locality_authorities.csv")
    capabilities=_rows("registry/me_locality_capabilities.csv")
    a={r["locality"] for r in authorities}
    c={r["locality"] for r in capabilities}
    assert len(authorities) == len(a)
    assert len(capabilities) == len(c)
    assert len(a) >= 100
    assert a == c
