from datetime import datetime, timezone

from election_data_grabber.adapters.washtenaw import WashtenawAdapter
from election_data_grabber.models import Format, Source, SourceKind, VoteMode


HTML = b"""
<html><head><title>Election</title></head><body>
<h2>City of Ann Arbor, Ward 1, Precinct 2</h2>
<div>This report created: Monday, Aug 31, 2026 11:33:05 AM</div>
<div>Registered Voters: 2,109</div>
<div>Ballots Cast: 526</div>
<table>
<tr><td>Governor DEM</td></tr>
<tr><td>Jocelyn Benson</td><td>81</td><td>210</td><td>122</td><td>413</td><td>86.85%</td></tr>
<tr><td>Christopher Robert Swanson</td><td>12</td><td>21</td><td>29</td><td>62</td><td>12.87%</td></tr>
</table>
</body></html>
"""


def source() -> Source:
    return Source(
        source_id="mi-washtenaw-live",
        jurisdiction="Washtenaw County",
        state="MI",
        url="https://electionresults.ewashtenaw.org/electionreporting/aug2026/precinctreport15.html",
        kind=SourceKind.OFFICIAL_WEB,
        format=Format.HTML,
        platform="washtenaw_enr",
        official=True,
        live_capable=True,
        precinct_level=True,
        vote_mode_detail=True,
    )


def test_washtenaw_preserves_modes_order_and_turnout_fields():
    adapter = WashtenawAdapter(source())
    fetched_at = datetime(2026, 8, 31, 16, 0, tzinfo=timezone.utc)
    rows = adapter.parse(HTML, fetched_at=fetched_at)

    assert len(rows) == 8
    first = rows[0]
    assert first.reporting_unit_name == "City of Ann Arbor, Ward 1, Precinct 2"
    assert first.contest_name == "Governor DEM"
    assert first.choice_name == "Jocelyn Benson"
    assert first.ballot_order == 1
    assert first.vote_mode == VoteMode.EARLY
    assert first.votes == 81
    assert first.registered_voters == 2109
    assert first.ballots_cast == 526

    benson = [r for r in rows if r.choice_name == "Jocelyn Benson"]
    assert [(r.vote_mode, r.votes) for r in benson] == [
        (VoteMode.EARLY, 81),
        (VoteMode.ABSENTEE, 210),
        (VoteMode.ELECTION_DAY, 122),
        (VoteMode.TOTAL, 413),
    ]

    swanson = [r for r in rows if r.choice_name == "Christopher Robert Swanson"]
    assert all(r.ballot_order == 2 for r in swanson)
