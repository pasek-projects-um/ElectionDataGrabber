from datetime import datetime, timezone

from election_data_grabber.adapters.ohio_tabulator_text import parse_ohio_tabulator_text
from election_data_grabber.reporting_unit_identity import AdapterReportingContext


NOW=datetime(2026,11,3,22,0,tzinfo=timezone.utc)
CTX=AdapterReportingContext(
    "OH",
    "2026-general",
    "us:oh:county:athens",
    "us:authority:oh:board-of-elections:athens-county-board-of-elections",
    "oh-athens-sov",
    "final",
    "certified",
    "a"*64,
)


def test_normalizes_conservative_precinct_sov_text():
    text="""Statement of Votes Cast
Precinct ATH 1
Registered Voters 1,200
Ballots Cast 650
Mayor
Alice 300
Bob 250
Undervotes 100
Precinct ATH 2
Registered Voters 900
Voters Cast 500
Mayor
Alice 280
Bob 180
"""
    rows=parse_ohio_tabulator_text(
        text,
        election_id="2026-general",
        source_id="oh-athens-sov",
        fetched_at=NOW,
        reporting_context=CTX,
    )
    assert len(rows)==4
    assert {r.reporting_unit_name for r in rows}=={"ATH 1","ATH 2"}
    assert {r.choice_name for r in rows}=={"Alice","Bob"}
    assert all(r.ballot_order is None for r in rows)
    assert [r.source_order for r in rows if r.reporting_unit_name=="ATH 1"]==[1,2]
    first=next(r for r in rows if r.reporting_unit_name=="ATH 1" and r.choice_name=="Alice")
    assert first.registered_voters==1200
    assert first.ballots_cast==650
    assert first.snapshot_sha256=="a"*64


def test_does_not_emit_metadata_or_totals_as_choices():
    text="""Precinct 001
Registered Voters 100
Ballots Cast 60
President
Alice 30
Bob 25
Total Votes 55
Overvotes 1
Undervotes 4
"""
    rows=parse_ohio_tabulator_text(
        text,
        election_id="2026-general",
        source_id="oh-athens-sov",
        fetched_at=NOW,
        reporting_context=CTX,
    )
    assert [r.choice_name for r in rows]==["Alice","Bob"]
