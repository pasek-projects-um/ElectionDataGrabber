from pathlib import Path

from scripts.promote_az_ky_surfaces import county_like_rows, summarize


def test_az_ky_promotion_filters_reached_surfaces(tmp_path: Path):
    p=tmp_path/"exp.csv"
    p.write_text(
        "state,authority_url,authority_host,result_links,election_night_candidate,smallest_observed_unit,platform_family,status\n"
        "AZ,https://a.gov,a.gov,https://a.gov/results,true,precinct,clarity,reached\n"
        "AZ,https://b.gov,b.gov,,,official_web,central_fetch_failed\n"
        "KY,https://k.gov,k.gov,https://k.gov/results,false,precinct,official_web,reached\n",
        encoding="utf-8",
    )
    rows=county_like_rows(p,{"AZ","KY"})
    assert len(rows)==2
    by={r["state"]:r for r in summarize(rows)}
    assert by["AZ"]["expected_primary_units"]=="15"
    assert by["AZ"]["election_night_candidates"]=="1"
    assert by["KY"]["surfaces_with_result_links"]=="1"
