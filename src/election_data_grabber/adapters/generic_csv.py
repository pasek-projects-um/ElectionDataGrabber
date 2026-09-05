from __future__ import annotations

import csv
import io
from datetime import datetime

from election_data_grabber.models import ResultObservation, VoteMode


MODE_ALIASES = {
    "election_day": VoteMode.ELECTION_DAY,
    "early_voting": VoteMode.EARLY,
    "early": VoteMode.EARLY,
    "absentee": VoteMode.ABSENTEE,
    "av_counting_boards": VoteMode.ABSENTEE,
    "mail": VoteMode.MAIL,
    "provisional": VoteMode.PROVISIONAL,
    "votes": VoteMode.TOTAL,
    "total": VoteMode.TOTAL,
}


def parse_generic_precinct_csv(
    body: bytes,
    *,
    election_id: str,
    jurisdiction_id: str,
    source_id: str,
    fetched_at: datetime,
) -> list[ResultObservation]:
    """Parse common normalized precinct CSV exports into long-form observations.

    This parser intentionally supports the OpenElections-like schema family and preserves
    mode-specific columns when present. It is a baseline adapter, not a substitute for
    source-specific parsing where ballot order or richer metadata are available.
    """
    text = body.decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(text))
    rows: list[ResultObservation] = []

    for raw in reader:
        precinct = (raw.get("precinct") or raw.get("reporting_unit") or "").strip()
        contest = (raw.get("office") or raw.get("contest") or "").strip()
        candidate = (raw.get("candidate") or raw.get("choice") or "").strip()
        party = (raw.get("party") or "").strip() or None
        if not precinct or not contest or not candidate:
            continue

        for column, mode in MODE_ALIASES.items():
            if column not in raw or raw[column] in (None, ""):
                continue
            try:
                votes = int(str(raw[column]).replace(",", "").strip())
            except ValueError:
                continue
            rows.append(
                ResultObservation(
                    election_id=election_id,
                    jurisdiction_id=jurisdiction_id,
                    reporting_unit_id=f"{jurisdiction_id}:{precinct}",
                    reporting_unit_name=precinct,
                    contest_name=contest,
                    choice_name=candidate,
                    party=party,
                    votes=votes,
                    vote_mode=mode,
                    source_id=source_id,
                    fetched_at=fetched_at,
                    raw_vote_mode=column,
                )
            )

    return rows
