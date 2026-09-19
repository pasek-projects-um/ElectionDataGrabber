from __future__ import annotations

import re
from datetime import datetime

from election_data_grabber.models import ResultObservation, VoteMode
from election_data_grabber.reporting_unit_identity import AdapterReportingContext, UnitType

_PRECINCT = re.compile(r"^\s*Precinct\s*[:\-]?\s*(.+?)\s*$", re.I)
_REGISTERED = re.compile(r"Registered\s+Voters\s*[:\-]?\s*([\d,]+)", re.I)
_BALLOTS = re.compile(r"(?:Ballots|Voters)\s+Cast\s*[:\-]?\s*([\d,]+)", re.I)
_CONTEST = re.compile(r"^(?!Precinct\b)(?!Registered\s+Voters\b)(?!Ballots\s+Cast\b)(?!Voters\s+Cast\b)(?!Turnout\b)(?!Total\s+Votes\b)(?!Overvotes?\b)(?!Undervotes?\b)([A-Za-z].*?)\s*$")
_CHOICE_VOTES = re.compile(r"^\s*(.+?)\s+([\d,]+)\s*$")
_SKIP = re.compile(r"^(Total\s+Votes|Overvotes?|Undervotes?|Write[- ]?Ins?|Times\s+Cast|Cards\s+Cast|Turnout)\b", re.I)


def parse_ohio_tabulator_text(
    text: str,
    *,
    election_id: str,
    source_id: str,
    fetched_at: datetime,
    reporting_context: AdapterReportingContext,
) -> list[ResultObservation]:
    """Normalize conservative text extraction from recurring Ohio precinct/SOV reports.

    The parser only emits rows after a precinct and contest header have both been
    observed. It preserves report order as source_order and never promotes it to
    ballot_order.
    """
    reporting_context.validate_call(election_id=election_id, source_id=source_id)

    out: list[ResultObservation] = []
    current_unit: str | None = None
    current_contest: str | None = None
    registered_voters: int | None = None
    ballots_cast: int | None = None
    source_order = 0

    lines = [re.sub(r"\s+", " ", line).strip() for line in text.splitlines()]
    for line in lines:
        if not line:
            continue

        precinct = _PRECINCT.match(line)
        if precinct:
            current_unit = precinct.group(1).strip()
            current_contest = None
            registered_voters = None
            ballots_cast = None
            source_order = 0
            continue

        registered = _REGISTERED.search(line)
        if registered:
            registered_voters = int(registered.group(1).replace(",", ""))
            continue

        ballots = _BALLOTS.search(line)
        if ballots:
            ballots_cast = int(ballots.group(1).replace(",", ""))
            continue

        if _SKIP.match(line):
            continue

        choice = _CHOICE_VOTES.match(line)
        if current_unit and current_contest and choice:
            name = choice.group(1).strip()
            if _SKIP.match(name):
                continue
            votes = int(choice.group(2).replace(",", ""))
            source_order += 1
            out.append(
                ResultObservation(
                    election_id=election_id,
                    jurisdiction_id=reporting_context.jurisdiction_id,
                    reporting_unit_id=reporting_context.unit_id(
                        UnitType.PRECINCT, current_unit, current_unit
                    ),
                    reporting_unit_name=current_unit,
                    reporting_regime_id=reporting_context.regime_id,
                    reporting_unit_raw_name=current_unit,
                    reporting_unit_source_native_id=current_unit,
                    snapshot_sha256=reporting_context.snapshot_sha256,
                    contest_name=current_contest,
                    choice_name=name,
                    source_order=source_order,
                    votes=votes,
                    vote_mode=VoteMode.TOTAL,
                    source_id=source_id,
                    fetched_at=fetched_at,
                    registered_voters=registered_voters,
                    ballots_cast=ballots_cast,
                    raw_vote_mode="total",
                )
            )
            continue

        if current_unit and _CONTEST.match(line):
            current_contest = line
            source_order = 0

    return out
