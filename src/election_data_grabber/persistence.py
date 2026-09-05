from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

from election_data_grabber.deltas import ResultDelta
from election_data_grabber.reconcile import ReconciliationResult
from election_data_grabber.washtenaw_ingest import WashtenawSummary


def write_integrity_outputs(
    root: Path,
    summary: WashtenawSummary,
    reconciliation: list[ReconciliationResult],
    deltas: list[ResultDelta] | None = None,
) -> None:
    """Persist machine-readable ingest diagnostics beside raw snapshots."""
    root.mkdir(parents=True, exist_ok=True)
    summary_payload = {
        "election_url": summary.election_url,
        "precinct_urls": summary.precinct_urls,
        "precincts_total": summary.precincts_total,
        "precincts_counted": summary.precincts_counted,
        "precincts_partially_counted": summary.precincts_partially_counted,
        "registered_voters": summary.registered_voters,
        "ballots_cast": summary.ballots_cast,
        "source_timestamp": summary.source_timestamp.isoformat() if summary.source_timestamp else None,
    }
    (root / "summary.json").write_text(json.dumps(summary_payload, indent=2, sort_keys=True), encoding="utf-8")
    rec = []
    for row in reconciliation:
        item = asdict(row)
        item["vote_mode"] = row.vote_mode.value
        item["reconciles"] = row.reconciles
        rec.append(item)
    (root / "reconciliation.json").write_text(json.dumps(rec, indent=2, sort_keys=True), encoding="utf-8")
    if deltas is not None:
        payload = []
        for row in deltas:
            item = asdict(row)
            for key, value in list(item.items()):
                if hasattr(value, "value"):
                    item[key] = value.value
            payload.append(item)
        (root / "deltas.json").write_text(json.dumps(payload, indent=2, sort_keys=True, default=str), encoding="utf-8")
