from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from election_data_grabber.models import Snapshot


@dataclass(frozen=True, slots=True)
class SnapshotRef:
    """Stable provenance reference for normalized records."""
    source_id: str
    sha256: str

    @classmethod
    def from_snapshot(cls, snapshot: Snapshot) -> "SnapshotRef":
        return cls(snapshot.source_id, snapshot.sha256)


def validate_snapshot(snapshot: Snapshot, *, require_body: bool = True) -> None:
    if len(snapshot.sha256) != 64 or any(c not in "0123456789abcdef" for c in snapshot.sha256.lower()):
        raise ValueError("snapshot sha256 must be a 64-character hexadecimal digest")
    if require_body and not Path(snapshot.body_path).is_file():
        raise FileNotFoundError(snapshot.body_path)


def attach_snapshot(records: list, snapshot: Snapshot) -> list:
    """Attach immutable snapshot provenance without changing adapter parsing APIs.

    This is the compatibility bridge while adapters are migrated to parse from
    Snapshot objects directly.
    """
    validate_snapshot(snapshot)
    for record in records:
        if record.source_id != snapshot.source_id:
            raise ValueError(
                f"source mismatch: record={record.source_id!r} snapshot={snapshot.source_id!r}"
            )
        record.snapshot_sha256 = snapshot.sha256
    return records


def require_snapshot_provenance(records: list) -> None:
    missing = [i for i, r in enumerate(records) if not getattr(r, "snapshot_sha256", None)]
    if missing:
        raise ValueError(f"normalized records missing snapshot provenance at indexes {missing[:10]}")
