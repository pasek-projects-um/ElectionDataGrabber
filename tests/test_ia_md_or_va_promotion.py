from pathlib import Path
from scripts.promote_ia_md_or_va_surfaces import promotable_rows, summarize


def test_promotes_only_reached_target_state_surfaces(tmp_path: Path):
    p=tmp_path/"exp.csv"
    p.write_text(
        "state,authority_url,authority_host,result_links,election_night_candidate,smallest_observed_unit,platform_family,status\n"
        "IA,https://a.gov,a.gov,https://a.gov/results,true,precinct,official_web,reached\n"
        "MD,https://m.gov,m.gov,https://m.gov/results,false,precinct,civicplus,reached\n"
        "OR,https://o.gov,o.gov,,,official_web,reached\n"
        "VA,https://v.gov,v.gov,https://v.gov/results,true,district,clarity,reached\n"
        "AZ,https://z.gov,z.gov,https://z.gov/results,true,precinct,clarity,reached\n"
        "IA,https://bad.gov,bad.gov,,,,central_fetch_failed\n",
        encoding="utf-8",
    )
    rows=promotable_rows(p)
    assert {r["state"] for r in rows}=={"IA","MD","OR","VA"}
    by={r["state"]:r for r in summarize(rows)}
    assert by["IA"]["expected_primary_units"]=="99"
    assert by["MD"]["surfaces_with_result_links"]=="1"
    assert by["OR"]["surfaces_with_result_links"]=="0"
    assert by["VA"]["election_night_candidates"]=="1"
