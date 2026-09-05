from datetime import datetime, timezone
from election_data_grabber.adapters.ohio_precinct_detail import OhioPrecinctDetailAdapter
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
def test_ballot_order_is_precinct_specific():
    s=Source(source_id="oh",jurisdiction="Athens County",state="OH",url="https://example.test",kind=SourceKind.OFFICIAL_WEB,format=Format.HTML)
    rows=OhioPrecinctDetailAdapter(s,"2024-general").parse(HTML,datetime.now(timezone.utc))
    order={(r.reporting_unit_name,r.choice_name):r.ballot_order for r in rows}
    assert order[("ATH 1","Alice")] == 1
    assert order[("ATH 1","Bob")] == 2
    assert order[("ATH 2","Bob")] == 1
    assert order[("ATH 2","Alice")] == 2
    assert all(r.ballot_order_scope=="reporting_unit" for r in rows)
