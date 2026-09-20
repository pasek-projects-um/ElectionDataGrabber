from pathlib import Path
from scripts.promote_mo_nh_hi_nj_surfaces import promotable_rows, summarize


def test_promotes_only_reached_target_state_surfaces(tmp_path: Path):
    p=tmp_path/"exp.csv"
    p.write_text(
        "state,authority_url,authority_host,result_links,election_night_candidate,smallest_observed_unit,platform_family,status\n"
        "MO,https://m.gov,m.gov,https://m.gov/results,true,precinct,clarity,reached\n"
        "NH,https://n.gov,n.gov,https://n.gov/results,false,ward,official_web,reached\n"
        "HI,https://h.gov,h.gov,,false,,official_web,reached\n"
        "NJ,https://j.gov,j.gov,https://j.gov/results,true,district,scytl,reached\n"
        "AZ,https://z.gov,z.gov,https://z.gov/results,true,precinct,clarity,reached\n"
        "MO,https://bad.gov,bad.gov,,false,,unknown_web,central_fetch_failed\n",
        encoding="utf-8",
    )
    rows=promotable_rows(p)
    assert {r["state"] for r in rows}=={"MO","NH","HI","NJ"}
    by={r["state"]:r for r in summarize(rows)}
    assert by["MO"]["expected_primary_units"]=="116"
    assert by["NH"]["precinct_or_finer_surfaces"]=="1"
    assert by["HI"]["surfaces_with_result_links"]=="0"
    assert by["NJ"]["election_night_candidates"]=="1"
