import csv
from pathlib import Path

def _rows(path):
    with Path(path).open(encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))

def test_pennsylvania_registry_covers_all_67_unique_counties():
    a=_rows("registry/pa_county_authorities.csv")
    c=_rows("registry/pa_county_capabilities.csv")
    an={r["county"] for r in a}; cn={r["county"] for r in c}
    assert len(a)==67 and len(an)==67
    assert len(c)==67 and len(cn)==67
    assert an==cn
