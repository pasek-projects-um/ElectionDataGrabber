from datetime import datetime, timezone

from election_data_grabber.adapters.ohio_precinct_detail import (
    OhioPrecinctDetailAdapter,
    discover_ohio_boe_reports,
)
from election_data_grabber.models import Format, Source, SourceKind


HTML=b"""
<table>
<tr><th>Precinct</th><td>ATH 1</td></tr>
<tr><td>President</td></tr>
<tr><td>Alice</td><td>10</td></tr><tr><td>Bob</td><td>8</td></tr>
<tr><th>Precinct</th><td>ATH 2</td></tr>
<tr><td>President</td></tr>
<tr><td>Bob</td><td>9</td></tr><tr><td>Alice</td><td>7</td></tr>
</table>
"""


def source():
    return Source(
        source_id="oh",
        jurisdiction="Athens County",
        state="OH",
        url="https://example.test",
        kind=SourceKind.OFFICIAL_WEB,
        format=Format.HTML,
    )


def test_report_order_is_not_assumed_to_be_ballot_order():
    rows=OhioPrecinctDetailAdapter(source(),"2024-general").parse(
        HTML,datetime.now(timezone.utc)
    )
    order={(r.reporting_unit_name,r.choice_name):r.source_order for r in rows}
    assert order[("ATH 1","Alice")] == 1
    assert order[("ATH 1","Bob")] == 2
    assert order[("ATH 2","Bob")] == 1
    assert order[("ATH 2","Alice")] == 2
    assert all(r.ballot_order is None for r in rows)


def test_discovers_standard_ohio_boe_report_family():
    page=b"""
    <a href="/a.pdf">November 5, 2024 Cumulative Results</a>
    <a href="/p.pdf">November 5, 2024 Precinct Detail</a>
    <a href="/o.pdf">November 5, 2024 Overlap Results</a>
    """
    reports=discover_ohio_boe_reports(page,"https://www.boe.ohio.gov/athens/results/")
    assert [r["kind"] for r in reports] == ["cumulative","precinct_detail","overlap"]
    assert reports[1]["url"] == "https://www.boe.ohio.gov/p.pdf"
