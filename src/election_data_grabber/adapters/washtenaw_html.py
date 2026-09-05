from __future__ import annotations

import re
from datetime import datetime

from bs4 import BeautifulSoup

from election_data_grabber.models import ResultObservation, VoteMode


MODE_HEADERS = {
    "early votes": VoteMode.EARLY,
    "absentee votes": VoteMode.ABSENTEE,
    "election day votes": VoteMode.ELECTION_DAY,
    "total votes": VoteMode.TOTAL,
}


def _int(text: str) -> int | None:
    digits = re.sub(r"[^0-9-]", "", text)
    if not digits:
        return None
    try:
        return int(digits)
    except ValueError:
        return None


def parse_washtenaw_like_html(
    body: bytes,
    *,
    election_id: str,
    jurisdiction_id: str,
    source_id: str,
    fetched_at: datetime,
) -> list[ResultObservation]:
    """Parse a simplified Washtenaw-style precinct result table.

    Fixture contract:
    - one element with class `reporting-unit`
    - one or more `.contest` blocks with a heading
    - table headers containing candidate plus mode columns
    - candidate rows preserving DOM order as ballot order
    """
    soup = BeautifulSoup(body.decode("utf-8", errors="replace"), "html.parser")
    unit_el = soup.select_one(".reporting-unit")
    unit_name = unit_el.get_text(" ", strip=True) if unit_el else ""
    if not unit_name:
        return []

    observations: list[ResultObservation] = []
    for contest in soup.select(".contest"):
        heading = contest.find(["h1", "h2", "h3", "h4"])
        contest_name = heading.get_text(" ", strip=True) if heading else ""
        table = contest.find("table")
        if not contest_name or table is None:
            continue
        headers = [th.get_text(" ", strip=True).lower() for th in table.find_all("th")]
        mode_columns = {idx: MODE_HEADERS[h] for idx, h in enumerate(headers) if h in MODE_HEADERS}
        candidate_idx = next((i for i, h in enumerate(headers) if h in {"candidate", "choice"}), 0)
        party_idx = next((i for i, h in enumerate(headers) if h == "party"), None)

        for order, tr in enumerate(table.find_all("tr")[1:], start=1):
            cells = [td.get_text(" ", strip=True) for td in tr.find_all(["td", "th"])]
            if not cells or candidate_idx >= len(cells):
                continue
            candidate = cells[candidate_idx].strip()
            if not candidate:
                continue
            party = cells[party_idx].strip() if party_idx is not None and party_idx < len(cells) else None
            for idx, mode in mode_columns.items():
                if idx >= len(cells):
                    continue
                votes = _int(cells[idx])
                if votes is None:
                    continue
                observations.append(
                    ResultObservation(
                        election_id=election_id,
                        jurisdiction_id=jurisdiction_id,
                        reporting_unit_id=f"{jurisdiction_id}:{unit_name}",
                        reporting_unit_name=unit_name,
                        contest_name=contest_name,
                        choice_name=candidate,
                        ballot_order=order,
                        party=party or None,
                        votes=votes,
                        vote_mode=mode,
                        source_id=source_id,
                        fetched_at=fetched_at,
                        raw_vote_mode=headers[idx],
                    )
                )
    return observations
