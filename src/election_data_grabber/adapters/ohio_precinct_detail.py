from __future__ import annotations

import re
from datetime import datetime

from bs4 import BeautifulSoup

from election_data_grabber.models import ResultObservation, Source, VoteMode


_INT = re.compile(r"[^0-9-]")
RESULT_LINK = re.compile(
    r"(cumulative|official results|precinct\s+detail|overlap|overlapping districts|results by groups)",
    re.I,
)


def _integer(value: str) -> int:
    value = _INT.sub("", value or "")
    return int(value) if value not in ("", "-") else 0


def discover_ohio_boe_reports(body: bytes, base_url: str) -> list[dict[str, str]]:
    """Discover recurring Ohio BOE result-report links from standardized pages."""
    from urllib.parse import urljoin

    soup = BeautifulSoup(body, "html.parser")
    out: list[dict[str, str]] = []
    for a in soup.find_all("a", href=True):
        label = " ".join(a.stripped_strings)
        m = RESULT_LINK.search(label)
        if not m:
            continue
        raw_kind = m.group(1).lower()
        kind = {
            "official results": "cumulative",
            "overlapping districts": "overlap",
            "results by groups": "group_detail",
        }.get(raw_kind, raw_kind.replace(" ", "_"))
        out.append({"kind": kind, "label": label, "url": urljoin(base_url, a["href"])})
    return out


class OhioPrecinctDetailAdapter:
    """Parse table-like Ohio precinct-detail artifacts.

    This parser is for HTML/table exports or fixtures. Many Ohio BOE Precinct
    Detail links are PDFs, so production ingestion should first extract the PDF
    into structured rows/text and then normalize with the same field semantics.

    Critically, report-column order is stored as source_order. It is NOT
    promoted to ballot_order unless an independent ballot/rotation source
    verifies the voter-facing order for that precinct.
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
            cells = [x.get_text(" ", strip=True) for x in row.select("th,td")]
            if not cells:
                continue
            joined = " ".join(cells)
            if re.search(r"\bprecinct\b", joined, re.I) and len(cells) <= 3:
                current_unit = cells[-1]
                current_contest = None
                order = 0
                continue
            if len(cells) == 1 and current_unit:
                current_contest = cells[0]
                order = 0
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
                    source_order=order,
                    votes=_integer(cells[-1]),
                    vote_mode=VoteMode.TOTAL,
                    source_id=self.source.source_id,
                    fetched_at=fetched_at,
                ))
        return out


def ohio_boe_urls(county_slug: str) -> dict[str, str]:
    """Standard Ohio SOS-hosted BOE endpoints used by many counties."""
    slug = county_slug.strip().lower().replace(" ", "-")
    return {
        "results": f"https://www.boe.ohio.gov/{slug}/election-info/election-results/",
        "precinct_polling": f"https://lookup.boe.ohio.gov/vtrapp/{slug}/precandpoll.aspx",
    }
