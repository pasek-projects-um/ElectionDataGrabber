import csv

from election_data_grabber.source_overlap import (
    OverlapCalibration,
    OverlapRelationship,
    SourceSnapshot,
)
from election_data_grabber.source_overlap_store import (
    calibration_row,
    snapshot_row,
    write_calibrations,
    write_snapshots,
)


def test_snapshot_row_preserves_replay_relevant_dimensions():
    row=snapshot_row(SourceSnapshot(
        "source-a","us:aa:county:x","2026-11-03T22:00:00Z",0.42,(100.0,80.0),
        frozenset({"p2","p1"}),frozenset({"mail","election_day"}),
    ))
    assert row["result_vector"]=="100.0|80.0"
    assert row["reporting_units"]=="p1|p2"
    assert row["vote_modes"]=="election_day|mail"


def test_calibration_row_keeps_independence_guardrail():
    row=calibration_row(OverlapCalibration(
        "a","b","j1",4,0.99,0.8,0.4,OverlapRelationship.PARTIAL_OVERLAP
    ))
    assert row["relationship"]=="partial_overlap"
    assert row["residual_independence_established"]=="False"


def test_csv_writers_emit_headers_and_rows(tmp_path):
    snapshots=tmp_path/"snapshots.csv"
    calibrations=tmp_path/"calibrations.csv"
    write_snapshots(snapshots,[SourceSnapshot("a","j1","t1",0.5,(1.0,2.0))])
    write_calibrations(calibrations,[OverlapCalibration(
        "a","b","j1",1,0.9,None,None,OverlapRelationship.UNCERTAIN
    )])
    with snapshots.open() as f:
        assert len(list(csv.DictReader(f)))==1
    with calibrations.open() as f:
        assert len(list(csv.DictReader(f)))==1
