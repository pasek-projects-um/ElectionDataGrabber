from __future__ import annotations

from datetime import datetime
from typing import Any

from election_data_grabber.models import ResultObservation, VoteMode
from election_data_grabber.reporting_unit_identity import AdapterReportingContext, UnitType
from election_data_grabber.vote_modes import normalize_vote_mode


def _state_from_jurisdiction(jurisdiction_id: str) -> str | None:
    parts = jurisdiction_id.lower().split(":")
    if len(parts) >= 2 and parts[0] == "us" and len(parts[1]) == 2:
        return parts[1].upper()
    for state in ("mi", "oh", "pa", "me"):
        if jurisdiction_id.lower().startswith(state + "-"):
            return state.upper()
    return None


def parse_generic_results_json(
    payload: dict[str, Any],
    *,
    election_id: str,
    jurisdiction_id: str,
    source_id: str,
    fetched_at: datetime,
    reporting_context: AdapterReportingContext | None = None,
    reporting_unit_type: UnitType = UnitType.PRECINCT,
) -> list[ResultObservation]:
    """Parse a simple contest -> choices JSON feed shape used as an adapter contract fixture.

    Expected shape:
    {"reporting_units": [{"id":..., "name":..., "contests": [{"name":...,
      "choices": [{"name":..., "party":..., "order":..., "votes":..., "mode":...}]}]}]}

    Vendor-specific adapters should transform their native payloads into this contract.
    """
    if reporting_context is not None:
        reporting_context.validate_call(election_id=election_id, source_id=source_id)
    observations: list[ResultObservation] = []
    state = _state_from_jurisdiction(reporting_context.jurisdiction_id if reporting_context else jurisdiction_id)
    for unit in payload.get("reporting_units", []):
        unit_id = str(unit.get("id") or unit.get("name") or "").strip()
        unit_name = str(unit.get("name") or unit_id).strip()
        if not unit_id:
            continue
        for contest in unit.get("contests", []):
            contest_name = str(contest.get("name") or "").strip()
            if not contest_name:
                continue
            for choice in contest.get("choices", []):
                name = str(choice.get("name") or "").strip()
                if not name:
                    continue
                mode_raw = str(choice.get("mode") or "total").strip()
                resolution = normalize_vote_mode(mode_raw, state=state, source_id=source_id)
                mode = resolution.vote_mode or VoteMode.UNKNOWN
                observations.append(
                    ResultObservation(
                        election_id=election_id,
                        jurisdiction_id=(reporting_context.jurisdiction_id if reporting_context else jurisdiction_id),
                        reporting_unit_id=(reporting_context.unit_id(reporting_unit_type, unit_name, unit_id) if reporting_context else f"{jurisdiction_id}:{unit_id}"),
                        reporting_unit_name=unit_name,
                        reporting_regime_id=(reporting_context.regime_id if reporting_context else None),
                        reporting_unit_raw_name=(unit_name if reporting_context else None),
                        reporting_unit_source_native_id=(unit_id if reporting_context else None),
                        snapshot_sha256=(reporting_context.snapshot_sha256 if reporting_context else None),
                        contest_name=contest_name,
                        choice_name=name,
                        source_order=choice.get("order"),
                        party=(str(choice.get("party")).strip() if choice.get("party") else None),
                        votes=int(choice.get("votes") or 0),
                        vote_mode=mode,
                        source_id=source_id,
                        fetched_at=fetched_at,
                        raw_vote_mode=mode_raw,
                        vote_mode_mapping_method=(resolution.rule.mapping_method if resolution.rule else None),
                        vote_mode_evidence_reference=(resolution.rule.evidence_reference if resolution.rule else None),
                    )
                )
    return observations
