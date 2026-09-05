from __future__ import annotations

import re
from datetime import datetime

from bs4 import BeautifulSoup

from election_data_grabber.adapters.base import Adapter
from election_data_grabber.models import ResultObservation, VoteMode


REPORT_TS_RE = re.compile(r"This report created:\s*(.+)")
INT_RE = re.compile(r"-?\d[\d,]*")


class WashtenawAdapter(Adapter):
    """Parse Washtenaw County's election-reporting HTML.

    The county exposes separate Early, Absentee, Election Day, and Total columns.
    This adapter preserves all four modes and candidate DOM order.
    """

    vote_modes = [
        VoteMode.EARLY,
        VoteMode.ABSENTEE,
        VoteMode.ELECTION_DAY,
        VoteMode.TOTAL,
    ]

    def parse(self, body: bytes, *, fetched_at: datetime) -> list[ResultObservation]:
        soup = BeautifulSoup(body, "html.parser")
        text = soup.get_text(" ", strip=True)
        report_ts = self._parse_report_timestamp(text)
        reporting_unit_name = self._reporting_unit_name(soup)
        reporting_unit_id = self._slug(reporting_unit_name)
        registered_voters = self._labeled_int(text, "Registered Voters")
        ballots_cast = self._labeled_int(text, "Ballots Cast")

        observations: list[ResultObservation] = []
        ballot_order = 0
        current_contest: str | None = None

        for row in soup.find_all("tr"):
            cells = [" ".join(c.stripped_strings) for c in row.find_all(["th", "td"])]
            if not cells:
                continue

            # Contest rows generally contain a contest label and no numeric vote columns.
            if len(cells) == 1 and not INT_RE.search(cells[0]):
                label = cells[0].strip()
                if label and label.lower() not in {
                    "summary",
                    "precincts counted",
                    "reports",
                    "map view",
                }:
                    current_contest = label
                    ballot_order = 0
                continue

            if current_contest is None or len(cells) < 5:
                continue

            choice = cells[0].strip()
            nums = [self._parse_int(x) for x in cells[1:5]]
            if any(x is None for x in nums):
                continue

            ballot_order += 1
            for mode, votes, raw_mode in zip(
                self.vote_modes,
                nums,
                ["Early Votes", "Absentee Votes", "Election Day Votes", "Total Votes"],
            ):
                observations.append(
                    ResultObservation(
                        election_id="2026-08-04-mi-primary",
                        jurisdiction_id="mi-washtenaw",
                        reporting_unit_id=reporting_unit_id,
                        reporting_unit_name=reporting_unit_name,
                        contest_name=current_contest,
                        choice_name=choice,
                        ballot_order=ballot_order,
                        votes=votes,
                        vote_mode=mode,
                        source_id=self.source.source_id,
                        fetched_at=fetched_at,
                        source_timestamp=report_ts,
                        registered_voters=registered_voters,
                        ballots_cast=ballots_cast,
                        raw_vote_mode=raw_mode,
                    )
                )
        return observations

    @staticmethod
    def _parse_int(value: str) -> int | None:
        match = INT_RE.search(value.replace("%", ""))
        return int(match.group(0).replace(",", "")) if match else None

    def _labeled_int(self, text: str, label: str) -> int | None:
        match = re.search(rf"{re.escape(label)}:\s*([\d,]+)", text, re.I)
        return int(match.group(1).replace(",", "")) if match else None

    @staticmethod
    def _parse_report_timestamp(text: str) -> datetime | None:
        match = REPORT_TS_RE.search(text)
        if not match:
            return None
        raw = match.group(1)
        raw = raw.split(" Registered Voters:", 1)[0].strip()
        for fmt in ("%A, %b %d, %Y %I:%M:%S %p", "%A, %B %d, %Y %I:%M:%S %p"):
            try:
                return datetime.strptime(raw, fmt)
            except ValueError:
                pass
        return None

    @staticmethod
    def _reporting_unit_name(soup: BeautifulSoup) -> str:
        for selector in ("h1", "h2", "h3"):
            node = soup.find(selector)
            if node:
                label = " ".join(node.stripped_strings)
                if label and "election" not in label.lower():
                    return label
        title = soup.title.string.strip() if soup.title and soup.title.string else "Washtenaw County"
        return title

    @staticmethod
    def _slug(value: str) -> str:
        return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-") or "washtenaw-county"
