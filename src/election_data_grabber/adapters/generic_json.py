from __future__ import annotations

from datetime import datetime
from typing import Any

from election_data_grabber.models import ResultObservation, VoteMode


def parse_generic_results_json(
    payload: dict[str, Any],
    *,
    election_id: str,
    jurisdiction_id: str,
    source_id: str,
    fetched_at: datetime,
) -> list[ResultObservation]:
    """Parse a simple contest -> choices JSON feed shape used as an adapter contract fixture.

    Expected shape:
    {"reporting_units": [{"id":..., "name":..., "contests": [{"name":...,
      "choices": [{"name":..., "party":..., "order":..., "votes":..., "mode":...}]}]}]}

    Vendor-specific adapters should transform their native payloads into this contract.
    """
    observations: list[ResultObservation] = []
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
                mode_raw = str(choice.get("mode") or "total").strip().lower()
                try:
                    mode = VoteMode(mode_raw)
                except ValueError:
                    mode = VoteMode.OTHER
                observations.append(
                    ResultObservation(
                        election_id=election_id,
                        jurisdiction_id=jurisdiction_id,
                        reporting_unit_id=f"{jurisdiction_id}:{unit_id}",
                        reporting_unit_name=unit_name,
                        contest_name=contest_name,
                        choice_name=name,
                        ballot_order=choice.get("order"),
                        party=(str(choice.get("party")).strip() if choice.get("party") else None),
                        votes=int(choice.get("votes") or 0),
                        vote_mode=mode,
                        source_id=source_id,
                        fetched_at=fetched_at,
                        raw_vote_mode=mode_raw,
                    )
                )
    return observations
