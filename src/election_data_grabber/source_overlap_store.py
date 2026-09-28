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
