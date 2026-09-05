from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from election_data_grabber.adapters.washtenaw import WashtenawAdapter
from election_data_grabber.models import ResultObservation, Snapshot


@dataclass(slots=True)
class WashtenawSummary:
    election_url: str
    precinct_urls: list[str]
    precincts_total: int | None = None
    precincts_counted: int | None = None
    precincts_partially_counted: int | None = None
    registered_voters: int | None = None
    ballots_cast: int | None = None
    source_timestamp: datetime | None = None
    contest_totals: list[ResultObservation] | None = None


def parse_summary(html: bytes, election_url: str) -> WashtenawSummary:
    soup = BeautifulSoup(html, "html.parser")
    text = soup.get_text(" ", strip=True)

    def labeled_int(label: str) -> int | None:
        import re

        match = re.search(rf"{re.escape(label)}\s*:?\s*([\d,]+)", text, re.I)
        return int(match.group(1).replace(",", "")) if match else None

    precinct_urls: list[str] = []
    seen: set[str] = set()
    for a in soup.find_all("a", href=True):
        href = str(a["href"])
        if "precinctreport" not in href.lower():
            continue
        url = urljoin(election_url, href)
        if url not in seen:
            seen.add(url)
            precinct_urls.append(url)

    # The summary page uses the same contest table shape as precinct pages.
    # Parse it through the canonical adapter so county aggregates retain ballot
    # order and Early/Absentee/Election Day/Total dimensions.
    summary_source = WashtenawAdapter._reporting_unit_name(soup)
    summary_observations: list[ResultObservation] = []
    try:
        # parse() only needs fetched_at for provenance; source timestamp remains
        # the page's own report timestamp.
        from datetime import timezone
        parsed_at = datetime.now(timezone.utc)
        # parse_summary has no adapter instance, so contest parsing is completed
        # by ingest_election below where the configured source is available.
    except Exception:
        parsed_at = None

    return WashtenawSummary(
        election_url=election_url,
        precinct_urls=sorted(precinct_urls),
        precincts_total=labeled_int("Total Precincts"),
        precincts_counted=labeled_int("Fully Counted Precincts"),
        precincts_partially_counted=labeled_int("Partially Counted Precincts"),
        registered_voters=labeled_int("Registered Voters"),
        ballots_cast=labeled_int("Ballots Cast"),
        source_timestamp=WashtenawAdapter._parse_report_timestamp(text),
        contest_totals=summary_observations,
    )


def ingest_election(
    adapter: WashtenawAdapter,
    election_url: str,
    snapshot_root: Path,
) -> tuple[WashtenawSummary, list[Snapshot], list[ResultObservation]]:
    """Fetch summary + all linked precinct pages and normalize observations."""
    summary_fetch = adapter.fetch_url(election_url)
    summary_snapshot = adapter.snapshot(summary_fetch, snapshot_root)
    summary = parse_summary(summary_fetch.body, election_url)
    summary.contest_totals = adapter.parse(summary_fetch.body, fetched_at=summary_fetch.fetched_at)

    snapshots = [summary_snapshot]
    observations: list[ResultObservation] = []

    for precinct_url in summary.precinct_urls:
        fetched = adapter.fetch_url(precinct_url)
        snapshots.append(adapter.snapshot(fetched, snapshot_root))
        observations.extend(adapter.parse(fetched.body, fetched_at=fetched.fetched_at))

    return summary, snapshots, observations
