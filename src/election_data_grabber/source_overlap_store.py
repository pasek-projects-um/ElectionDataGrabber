from __future__ import annotations

import csv
from dataclasses import asdict
from pathlib import Path

from election_data_grabber.source_overlap import OverlapCalibration


CALIBRATION_FIELDS = (
    "left_source_id",
    "right_source_id",
    "jurisdiction_id",
    "matched_snapshot_count",
    "mean_vector_similarity",
    "reporting_unit_jaccard",
    "vote_mode_jaccard",
    "relationship",
    "residual_independence_established",
    "notes",
)


def calibration_row(calibration: OverlapCalibration) -> dict[str, str]:
    raw=asdict(calibration)
    raw["relationship"]=calibration.relationship.value
    return {field: str(raw[field]) if raw[field] is not None else "" for field in CALIBRATION_FIELDS}


def write_calibrations(path: Path, calibrations: list[OverlapCalibration]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer=csv.DictWriter(f, fieldnames=CALIBRATION_FIELDS)
        writer.writeheader()
        writer.writerows(calibration_row(c) for c in calibrations)


from election_data_grabber.source_overlap import SourceSnapshot

SNAPSHOT_FIELDS = (
    "source_id",
    "jurisdiction_id",
    "captured_at",
    "reporting_fraction",
    "result_vector",
    "reporting_units",
    "vote_modes",
)


def snapshot_row(snapshot: SourceSnapshot) -> dict[str, str]:
    return {
        "source_id": snapshot.source_id,
        "jurisdiction_id": snapshot.jurisdiction_id,
        "captured_at": snapshot.captured_at,
        "reporting_fraction": "" if snapshot.reporting_fraction is None else str(snapshot.reporting_fraction),
        "result_vector": "|".join(str(v) for v in snapshot.result_vector),
        "reporting_units": "|".join(sorted(snapshot.reporting_units)),
        "vote_modes": "|".join(sorted(snapshot.vote_modes)),
    }


def write_snapshots(path: Path, snapshots: list[SourceSnapshot]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer=csv.DictWriter(f, fieldnames=SNAPSHOT_FIELDS)
        writer.writeheader()
        writer.writerows(snapshot_row(s) for s in snapshots)
