from __future__ import annotations

import csv
import io
from datetime import datetime

from election_data_grabber.models import ResultObservation, VoteMode
from election_data_grabber.reporting_unit_identity import AdapterReportingContext, UnitType
from election_data_grabber.vote_modes import normalize_vote_mode


COLUMN_ALIASES = {
    "precinct": ("precinct", "reporting_unit", "ward_precinct", "precinct_name", "polling_place"),
    "contest": ("office", "contest", "race", "contest_name"),
    "candidate": ("candidate", "choice", "candidate_name", "option"),
    "party": ("party", "candidate_party"),
    "source_order": ("source_order", "order", "position", "ballot_order"),
    "registered_voters": ("registered_voters", "registered", "registration"),
    "ballots_cast": ("ballots_cast", "total_ballots", "ballots"),
}

VOTE_COLUMNS = (
    "election_day", "ed", "early_voting", "early", "absentee", "av",
    "av_counting_boards", "pre_process_absentee", "mail", "provisional",
    "votes", "total",
)


def _first(raw: dict[str, str | None], aliases: tuple[str, ...]) -> str | None:
    for key in aliases:
        value = raw.get(key)
        if value is not None and str(value).strip() != "":
            return str(value).strip()
    return None


def _int(value: str | None) -> int | None:
    if value is None or value == "":
        return None
    try:
        return int(value.replace(",", "").strip())
    except ValueError:
        return None


def _state_from_jurisdiction(jurisdiction_id: str) -> str | None:
    parts = jurisdiction_id.lower().split(":")
    if len(parts) >= 2 and parts[0] == "us" and len(parts[1]) == 2:
        return parts[1].upper()
    if jurisdiction_id.lower().startswith("mi-"):
        return "MI"
    if jurisdiction_id.lower().startswith("oh-"):
        return "OH"
    if jurisdiction_id.lower().startswith("pa-"):
        return "PA"
    if jurisdiction_id.lower().startswith("me-"):
        return "ME"
    return None


def parse_generic_precinct_csv(
    body: bytes,
    *,
    election_id: str,
    jurisdiction_id: str,
    source_id: str,
    fetched_at: datetime,
    reporting_context: AdapterReportingContext | None = None,
) -> list[ResultObservation]:
    if reporting_context is not None:
        reporting_context.validate_call(election_id=election_id, source_id=source_id)
    text = body.decode("utf-8-sig", errors="replace")
    reader = csv.DictReader(io.StringIO(text))
    rows: list[ResultObservation] = []
    state = _state_from_jurisdiction(reporting_context.jurisdiction_id if reporting_context else jurisdiction_id)

    for source_raw in reader:
        raw = {(k or "").strip().lower(): v for k, v in source_raw.items()}
        precinct = _first(raw, COLUMN_ALIASES["precinct"])
        contest = _first(raw, COLUMN_ALIASES["contest"])
        candidate = _first(raw, COLUMN_ALIASES["candidate"])
        party = _first(raw, COLUMN_ALIASES["party"])
        source_order = _int(_first(raw, COLUMN_ALIASES["source_order"]))
        registered_voters = _int(_first(raw, COLUMN_ALIASES["registered_voters"]))
        ballots_cast = _int(_first(raw, COLUMN_ALIASES["ballots_cast"]))
        if not precinct or not contest or not candidate:
            continue

        for column in VOTE_COLUMNS:
            if column not in raw or raw[column] in (None, ""):
                continue
            votes = _int(str(raw[column]))
            if votes is None:
                continue
            resolution = normalize_vote_mode(column, state=state, source_id=source_id)
            mode = resolution.vote_mode or VoteMode.UNKNOWN
            rows.append(ResultObservation(
                election_id=election_id,
                jurisdiction_id=(reporting_context.jurisdiction_id if reporting_context else jurisdiction_id),
                reporting_unit_id=(reporting_context.unit_id(UnitType.PRECINCT, precinct, precinct) if reporting_context else f"{jurisdiction_id}:{precinct}"),
                reporting_unit_name=precinct,
                reporting_regime_id=(reporting_context.regime_id if reporting_context else None),
                reporting_unit_raw_name=(precinct if reporting_context else None),
                reporting_unit_source_native_id=(precinct if reporting_context else None),
                snapshot_sha256=(reporting_context.snapshot_sha256 if reporting_context else None),
                contest_name=contest,
                choice_name=candidate,
                source_order=source_order,
                party=party,
                votes=votes,
                vote_mode=mode,
                source_id=source_id,
                fetched_at=fetched_at,
                registered_voters=registered_voters,
                ballots_cast=ballots_cast,
                raw_vote_mode=column,
                vote_mode_mapping_method=(resolution.rule.mapping_method if resolution.rule else None),
                vote_mode_evidence_reference=(resolution.rule.evidence_reference if resolution.rule else None),
            ))

    return rows
