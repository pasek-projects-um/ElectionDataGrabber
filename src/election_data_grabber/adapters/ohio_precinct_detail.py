from __future__ import annotations

import re
from datetime import datetime
from bs4 import BeautifulSoup

from election_data_grabber.models import ResultObservation, Source, VoteMode


_INT = re.compile(r"[^0-9-]")


def _integer(value: str) -> int:
    value = _INT.sub("", value or "")
    return int(value) if value not in ("", "-") else 0


class OhioPrecinctDetailAdapter:
    """Parser for Ohio's recurring precinct-detail HTML/report-table shape.

    Candidate order is deliberately derived inside each precinct/contest block.
    Ohio ballot rotation means a countywide candidate order must never be
    propagated down to precinct observations.
    """

    def __init__(self, source: Source, election_id: str):
        self.source = source
        self.election_id = election_id

    def parse(self, body: bytes, fetched_at: datetime) -> list[ResultObservation]:
        soup = BeautifulSoup(body, "html.parser")
        out: list[ResultObservation] = []
        current_unit = None
        current_contest = None
        order = 0
        for row in soup.select("tr"):
            cells=[x.get_text(" ",strip=True) for x in row.select("th,td")]
            if not cells:
                continue
            joined=" ".join(cells)
            # Common report exports label precinct blocks explicitly.
            if re.search(r"\bprecinct\b", joined, re.I) and len(cells) <= 3:
                current_unit=cells[-1]
                current_contest=None
                order=0
                continue
            if len(cells) == 1 and current_unit:
                current_contest=cells[0]
                order=0
                continue
            if current_unit and current_contest and len(cells) >= 2 and re.search(r"\d", cells[-1]):
                order += 1
                out.append(ResultObservation(
                    election_id=self.election_id,
                    jurisdiction_id=self.source.jurisdiction,
                    reporting_unit_id=current_unit,
                    reporting_unit_name=current_unit,
                    contest_name=current_contest,
                    choice_name=cells[0],
                    ballot_order=order,
                    ballot_order_scope="reporting_unit",
                    votes=_integer(cells[-1]),
                    vote_mode=VoteMode.TOTAL,
                    source_id=self.source.source_id,
                    fetched_at=fetched_at,
                ))
        return out
