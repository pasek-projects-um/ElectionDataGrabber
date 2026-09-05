from __future__ import annotations

import csv
import io
from datetime import datetime

from election_data_grabber.models import ResultObservation, VoteMode


MODE_ALIASES = {
    "election_day": VoteMode.ELECTION_DAY,
    "ed": VoteMode.ELECTION_DAY,
    "early_voting": VoteMode.EARLY,
    "early": VoteMode.EARLY,
    "absentee": VoteMode.ABSENTEE,
    "av": VoteMode.ABSENTEE,
    "av_counting_boards": VoteMode.ABSENTEE,
    "pre_process_absentee": VoteMode.ABSENTEE,
    "mail": VoteMode.MAIL,
    "provisional": VoteMode.PROVISIONAL,
    "votes": VoteMode.TOTAL,
    "total": VoteMode.TOTAL,
}

COLUMN_ALIASES = {
    "precinct": ("precinct", "reporting_unit", "ward_precinct", "precinct_name", "polling_place"),
    "contest": ("office", "contest", "race", "contest_name"),
    "candidate": ("candidate", "choice", "candidate_name", "option"),
    "party": ("party", "candidate_party"),
    "ballot_order": ("ballot_order", "order", "position"),
    "registered_voters": ("registered_voters", "registered", "registration"),
    "ballots_cast": ("ballots_cast", "total_ballots", "ballots"),
}


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


def parse_generic_precinct_csv(
    body: bytes,
    *,
    election_id: str,
    jurisdiction_id: str,
    source_id: str,
    fetched_at: datetime,
) -> list[ResultObservation]:
    """Parse common precinct CSV exports into canonical long-form observations.

    The parser is alias-driven so most new localities should be onboarded by
    registering a source/profile, not by writing another scraper. Richer source-
    specific adapters can still supersede this when ballot topology or metadata
    require it.
    """
    text = body.decode("utf-8-sig", errors="replace")
    reader = csv.DictReader(io.StringIO(text))
    rows: list[ResultObservation] = []

    for source_raw in reader:
        raw = {(k or "").strip().lower(): v for k, v in source_raw.items()}
        precinct = _first(raw, COLUMN_ALIASES["precinct"])
        contest = _first(raw, COLUMN_ALIASES["contest"])
        candidate = _first(raw, COLUMN_ALIASES["candidate"])
        party = _first(raw, COLUMN_ALIASES["party"])
        ballot_order = _int(_first(raw, COLUMN_ALIASES["ballot_order"]))
        registered_voters = _int(_first(raw, COLUMN_ALIASES["registered_voters"]))
        ballots_cast = _int(_first(raw, COLUMN_ALIASES["ballots_cast"]))
        if not precinct or not contest or not candidate:
            continue

        for column, mode in MODE_ALIASES.items():
            if column not in raw or raw[column] in (None, ""):
                continue
            votes = _int(str(raw[column]))
            if votes is None:
                continue
            rows.append(
                ResultObservation(
                    election_id=election_id,
                    jurisdiction_id=jurisdiction_id,
                    reporting_unit_id=f"{jurisdiction_id}:{precinct}",
                    reporting_unit_name=precinct,
                    contest_name=contest,
                    choice_name=candidate,
                    ballot_order=ballot_order,
                    party=party,
                    votes=votes,
                    vote_mode=mode,
                    source_id=source_id,
                    fetched_at=fetched_at,
                    registered_voters=registered_voters,
                    ballots_cast=ballots_cast,
                    raw_vote_mode=column,
                )
            )

    return rows
