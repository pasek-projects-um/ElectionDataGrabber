import csv
from pathlib import Path


def test_electproject_coverage_has_all_states_and_dc():
    root=Path(__file__).resolve().parents[1]
    with (root/"audit/electproject_2020_coverage_status.csv").open(encoding="utf-8",newline="") as f:
        rows=list(csv.DictReader(f))
    expected={
        "AK","AL","AR","AZ","CA","CO","CT","DC","DE","FL","GA","HI","IA","ID","IL","IN","KS","KY",
        "LA","MA","MD","ME","MI","MN","MO","MS","MT","NC","ND","NE","NH","NJ","NM","NV","NY","OH",
        "OK","OR","PA","RI","SC","SD","TN","TX","UT","VA","VT","WA","WI","WV","WY"
    }
    assert {r["state"] for r in rows} == expected
    assert len(rows)==51
    assert all(r["harvest_status"] and r["harvest_status"]!="pending" for r in rows)


def test_direct_url_rows_have_source_urls():
    root=Path(__file__).resolve().parents[1]
    with (root/"audit/electproject_2020_coverage_status.csv").open(encoding="utf-8",newline="") as f:
        rows=list(csv.DictReader(f))
    direct=[r for r in rows if r["harvest_status"] in {"direct_official_url","official_social_reference","official_file_share","official_dashboard_candidate"}]
    assert direct
    assert all(r["source_url"] for r in direct)
