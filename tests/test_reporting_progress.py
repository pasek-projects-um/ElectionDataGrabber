from datetime import datetime, timezone

from election_data_grabber.adapters.enhanced_voting import parse_enhanced_voting_progress
from election_data_grabber.adapters.washtenaw import WashtenawAdapter
from election_data_grabber.models import (
    Format,
    ReportingProgressBasis,
    ReportingProgressKind,
    ReportingProgressScope,
    Source,
    SourceKind,
    UpdateSemantics,
)
from election_data_grabber.reporting_progress import validate_progress_history


def _washtenaw_source() -> Source:
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


def test_washtenaw_progress_distinguishes_exists_from_inferred_reported_without_completion():
    html=b"""
    <html><body>
    <h2>City of Ann Arbor, Ward 1, Precinct 2</h2>
    <div>This report created: Monday, Aug 31, 2026 11:33:05 AM</div>
    <table>
      <tr><td>Governor DEM</td></tr>
      <tr><td>Alice</td><td>1</td><td>2</td><td>3</td><td>6</td></tr>
    </table>
    </body></html>
    """
    rows=WashtenawAdapter(_washtenaw_source()).parse_progress(
        html,
        fetched_at=datetime(2026,8,31,16,0,tzinfo=timezone.utc),
    )
    assert [r.kind for r in rows] == [
        ReportingProgressKind.UNIT_EXISTS,
        ReportingProgressKind.UNIT_REPORTED,
    ]
    assert rows[0].basis == ReportingProgressBasis.INFERRED
    assert rows[1].basis == ReportingProgressBasis.INFERRED
    assert rows[1].reported is True
    assert all(r.complete is None for r in rows)
    assert all(r.update_semantics == UpdateSemantics.UNKNOWN for r in rows)


def test_enhanced_progress_preserves_source_counts_completion_and_semantics():
    import json
    payload={"props":{"pageProps":{"status":{
        "precinctsReporting":7,
        "precinctsTotal":10,
        "isComplete":False,
        "isCumulative":True,
    }}}}
    html=f'<script id="__NEXT_DATA__" type="application/json">{json.dumps(payload)}</script>'.encode()
    rows=parse_enhanced_voting_progress(
        html,
        election_id="e1",
        jurisdiction_id="us:mi:county:test",
        source_id="enhanced",
        fetched_at=datetime(2026,11,3,22,0,tzinfo=timezone.utc),
    )
    counts=next(r for r in rows if r.kind == ReportingProgressKind.SOURCE_COUNTS)
    complete=next(r for r in rows if r.kind == ReportingProgressKind.SOURCE_COMPLETE)
    assert (counts.reporting_count, counts.expected_count) == (7,10)
    assert counts.basis == ReportingProgressBasis.SOURCE_REPORTED
    assert counts.update_semantics == UpdateSemantics.CUMULATIVE
    assert complete.complete is False
    assert complete.basis == ReportingProgressBasis.SOURCE_REPORTED


def test_progress_transition_history_is_monotonic_when_source_counts_are_cumulative():
    import json
    def parse(n):
        payload={"status":{"precinctsReporting":n,"precinctsTotal":10,"isCumulative":True}}
        html=f'<script type="application/json">{json.dumps(payload)}</script>'.encode()
        return next(
            r for r in parse_enhanced_voting_progress(
                html,
                election_id="e1",
                jurisdiction_id="us:mi:county:test",
                source_id="enhanced",
                fetched_at=datetime(2026,11,3,22,n,tzinfo=timezone.utc),
            )
            if r.kind == ReportingProgressKind.SOURCE_COUNTS
        )
    history=[parse(2),parse(6),parse(10)]
    assert [r.reporting_count for r in history] == [2,6,10]
    assert all(r.update_semantics == UpdateSemantics.CUMULATIVE for r in history)



def test_generic_reporting_key_is_not_misread_as_precinct_count():
    import json
    payload={"status":{"reporting":7,"complete":"final"}}
    html=f'<script type="application/json">{json.dumps(payload)}</script>'.encode()
    rows=parse_enhanced_voting_progress(
        html,election_id="e1",jurisdiction_id="us:mi:county:test",source_id="enhanced",
        fetched_at=datetime(2026,11,3,22,0,tzinfo=timezone.utc),
    )
    assert all(r.kind != ReportingProgressKind.SOURCE_COUNTS for r in rows)
    assert all(r.kind != ReportingProgressKind.SOURCE_COMPLETE for r in rows)


def test_false_cumulative_flag_does_not_claim_cumulative_semantics():
    import json
    payload={"status":{"precinctsReporting":7,"precinctsTotal":10,"isCumulative":False}}
    html=f'<script type="application/json">{json.dumps(payload)}</script>'.encode()
    row=next(r for r in parse_enhanced_voting_progress(
        html,election_id="e1",jurisdiction_id="us:mi:county:test",source_id="enhanced",
        fetched_at=datetime(2026,11,3,22,0,tzinfo=timezone.utc),
    ) if r.kind == ReportingProgressKind.SOURCE_COUNTS)
    assert row.update_semantics == UpdateSemantics.UNKNOWN


def test_progress_history_reports_cumulative_regression_without_mutating_snapshots():
    import json
    def parse(n,minute):
        payload={"status":{"precinctsReporting":n,"precinctsTotal":10,"isCumulative":True}}
        html=f'<script type="application/json">{json.dumps(payload)}</script>'.encode()
        return next(r for r in parse_enhanced_voting_progress(
            html,election_id="e1",jurisdiction_id="us:mi:county:test",source_id="enhanced",
            fetched_at=datetime(2026,11,3,22,minute,tzinfo=timezone.utc),
        ) if r.kind == ReportingProgressKind.SOURCE_COUNTS)
    rows=[parse(8,1),parse(6,2)]
    findings=validate_progress_history(rows)
    assert len(findings) == 1
    assert "cumulative reporting_count decreased 8->6" in findings[0]
    assert [r.reporting_count for r in rows] == [8,6]


def test_reporting_progress_scope_is_structured():
    import json
    payload={"status":{"precinctsReporting":1,"precinctsTotal":2}}
    html=f'<script type="application/json">{json.dumps(payload)}</script>'.encode()
    row=next(r for r in parse_enhanced_voting_progress(
        html,election_id="e1",jurisdiction_id="us:mi:county:test",source_id="enhanced",
        fetched_at=datetime(2026,11,3,22,0,tzinfo=timezone.utc),
    ) if r.kind == ReportingProgressKind.SOURCE_COUNTS)
    assert row.scope == ReportingProgressScope.SOURCE
