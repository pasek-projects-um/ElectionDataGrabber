from pathlib import Path
from scripts.classify_mn_next_action import classify_rows


def test_mn_reached_without_results_requires_inspection(tmp_path: Path):
    p=tmp_path/"exp.csv"
    p.write_text(
        "state,authority_url,authority_host,result_links,election_night_candidate,smallest_observed_unit,platform_family,status\n"
        "MN,https://mn.gov,mn.gov,,false,,unknown_web,reached\n"
        "AZ,https://az.gov,az.gov,https://az.gov/results,true,precinct,clarity,reached\n",
        encoding="utf-8",
    )
    rows=classify_rows(p)
    assert len(rows)==1
    assert rows[0]["state"]=="MN"
    assert rows[0]["next_action"]=="inspect_reached_authority"
