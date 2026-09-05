from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime

from bs4 import BeautifulSoup

from election_data_grabber.models import ResultObservation, VoteMode


MODE_LABELS = {
    "early": VoteMode.EARLY,
    "early voting": VoteMode.EARLY,
    "absentee": VoteMode.ABSENTEE,
    "av": VoteMode.ABSENTEE,
    "election day": VoteMode.ELECTION_DAY,
    "ed": VoteMode.ELECTION_DAY,
    "provisional": VoteMode.PROVISIONAL,
    "mail": VoteMode.MAIL,
    "total": VoteMode.TOTAL,
    "total votes": VoteMode.TOTAL,
}


@dataclass(frozen=True, slots=True)
class HtmlTableProfile:
    contest_selector: str | None = None
    reporting_unit_selector: str | None = None


def parse_mode_table_html(
    body: bytes,
    *,
    election_id: str,
    jurisdiction_id: str,
    source_id: str,
    fetched_at: datetime,
    profile: HtmlTableProfile = HtmlTableProfile(),
) -> list[ResultObservation]:
    """Parse common county result tables by recognizing semantic headers.

    This intentionally favors header inference over fixed column positions so
    minor vendor/template changes do not require a new parser.
    """
    soup = BeautifulSoup(body, "html.parser")
    reporting_unit = jurisdiction_id
    if profile.reporting_unit_selector:
        node = soup.select_one(profile.reporting_unit_selector)
        if node:
            reporting_unit = " ".join(node.stripped_strings)

    observations: list[ResultObservation] = []
    for table in soup.find_all("table"):
        rows = table.find_all("tr")
        if not rows:
            continue
        headers = [" ".join(x.stripped_strings).strip().lower() for x in rows[0].find_all(["th", "td"])]
        mode_cols: dict[int, tuple[VoteMode, str]] = {}
        for i, header in enumerate(headers):
            normalized = re.sub(r"\s+", " ", header)
            for label, mode in MODE_LABELS.items():
                if label == normalized or label in normalized:
                    mode_cols[i] = (mode, header)
                    break
        if not mode_cols:
            continue
        for row in rows[1:]:
            cells = [" ".join(x.stripped_strings).strip() for x in row.find_all(["th", "td"])]
            if len(cells) < 2:
                continue
            choice = cells[0]
            if not choice:
                continue
            contest = table.get("data-contest") or (profile.contest_selector and soup.select_one(profile.contest_selector))
            if hasattr(contest, "stripped_strings"):
                contest = " ".join(contest.stripped_strings)
            contest_name = str(contest or "unknown contest")
            for idx, (mode, raw_label) in mode_cols.items():
                if idx >= len(cells):
                    continue
                m = re.search(r"-?\d[\d,]*", cells[idx])
                if not m:
                    continue
                observations.append(ResultObservation(
                    election_id=election_id,
                    jurisdiction_id=jurisdiction_id,
                    reporting_unit_id=f"{jurisdiction_id}:{reporting_unit}",
                    reporting_unit_name=reporting_unit,
                    contest_name=contest_name,
                    choice_name=choice,
                    votes=int(m.group(0).replace(",", "")),
                    vote_mode=mode,
                    source_id=source_id,
                    fetched_at=fetched_at,
                    raw_vote_mode=raw_label,
                ))
    return observations
