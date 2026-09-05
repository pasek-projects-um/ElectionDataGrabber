from datetime import datetime, timezone

from election_data_grabber.adapters.washtenaw import WashtenawAdapter
from election_data_grabber.models import Source, SourceKind, VoteMode
from election_data_grabber.washtenaw_ingest import parse_summary


HTML = b"""
<html><body>
<h2>Washtenaw County</h2>
<div>Total Precincts: 112 Fully Counted Precincts: 110 Partially Counted Precincts: 2</div>
<div>Registered Voters: 300,000 Ballots Cast: 120,000</div>
<div>This report created: Tuesday, Aug 04, 2026 10:30:00 PM</div>
<a href="precinctreport.php?precinct=1">P1</a>
<table>
<tr><td>Governor</td></tr>
<tr><td>Candidate A</td><td>10,000</td><td>20,000</td><td>30,000</td><td>60,000</td></tr>
<tr><td>Candidate B</td><td>8,000</td><td>12,000</td><td>25,000</td><td>45,000</td></tr>
</table>
</body></html>
"""


def test_summary_metadata_and_contest_totals():
    summary = parse_summary(HTML, "https://example.test/results/")
    assert summary.precincts_total == 112
    assert summary.precincts_counted == 110
    assert summary.precincts_partially_counted == 2
    assert summary.registered_voters == 300000
    assert summary.ballots_cast == 120000
    assert len(summary.precinct_urls) == 1


def test_adapter_parses_county_summary_modes():
    source = Source(source_id="washtenaw", name="Washtenaw", url="https://example.test/results/", kind=SourceKind.HTML)
    adapter = WashtenawAdapter(source)
    rows = adapter.parse(HTML, fetched_at=datetime(2026, 8, 5, 2, 30, tzinfo=timezone.utc))
    totals = {(r.choice_name, r.vote_mode): r.votes for r in rows}
    assert totals[("Candidate A", VoteMode.EARLY)] == 10000
    assert totals[("Candidate A", VoteMode.ABSENTEE)] == 20000
    assert totals[("Candidate A", VoteMode.ELECTION_DAY)] == 30000
    assert totals[("Candidate A", VoteMode.TOTAL)] == 60000
