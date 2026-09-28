import csv
from pathlib import Path

EXPECTED_STATES={
    "CO","CT","GA","ID","IN","LA","MA","NC","NH","NM","NY","SC","UT","VA","VT"
}

def test_downballotr_official_source_leads_cover_all_supported_states():
    root=Path(__file__).resolve().parents[1]
    with (root/"audit/downballotr_official_source_leads.csv").open(encoding="utf-8",newline="") as f:
        rows=list(csv.DictReader(f))
    assert {r["state"] for r in rows} == EXPECTED_STATES
    assert all(r["source_url"].startswith("https://") for r in rows)
    assert all(r["origin_locator"] for r in rows)
