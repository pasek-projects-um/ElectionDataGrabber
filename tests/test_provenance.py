from datetime import datetime, timezone
from pathlib import Path

import pytest

from election_data_grabber.models import ResultObservation, Snapshot
from election_data_grabber.provenance import attach_snapshot, require_snapshot_provenance


def observation(source_id="s"):
    return ResultObservation(
        election_id="e", jurisdiction_id="j", reporting_unit_id="r",
        reporting_unit_name="R", contest_name="C", choice_name="X",
        votes=1, source_id=source_id, fetched_at=datetime.now(timezone.utc),
    )


def snapshot(tmp_path: Path, source_id="s"):
    body=tmp_path/"body"
    body.write_bytes(b"x")
    return Snapshot(
        source_id=source_id, fetched_at=datetime.now(timezone.utc),
        url="https://example.gov/results", http_status=200,
        sha256="2"*64, body_path=str(body),
    )


def test_attach_snapshot_provenance(tmp_path):
    rows=[observation()]
    attach_snapshot(rows,snapshot(tmp_path))
    assert rows[0].snapshot_sha256=="2"*64
    require_snapshot_provenance(rows)


def test_source_mismatch_fails(tmp_path):
    with pytest.raises(ValueError):
        attach_snapshot([observation("a")],snapshot(tmp_path,"b"))


def test_persistence_guard_rejects_unlinked_records():
    with pytest.raises(ValueError):
        require_snapshot_provenance([observation()])
