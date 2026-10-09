"""Inspect observed payload schemas without granting jurisdiction or live coverage."""

from __future__ import annotations

import csv
import io
import re

from bs4 import BeautifulSoup

MD_COLUMNS = [f"Congressional District {i}" for i in range(1, 9)]


def count(value):
    """Only nonnegative integer vote counts; missing values are not zero."""
    value = str(value).strip()
    if not re.fullmatch(r"(?:\d+|\d{1,3}(?:,\d{3})+)", value):
        raise ValueError("Invalid vote count")
    return int(value.replace(",", ""))


def maryland_congressional_csv(body):
    """Recognize the observed district breakdown, keeping county totals distinct."""
    reader = csv.DictReader(io.StringIO(body.lstrip("\ufeff")), skipinitialspace=True)
    reader.fieldnames = [c.strip() for c in (reader.fieldnames or [])]
    required = {
        "County",
        "County Name",
        "Office Name",
        "Office District",
        "Candidate Name",
        "Party",
        *MD_COLUMNS,
    }
    if not required.issubset(reader.fieldnames or []):
        raise ValueError("Unsupported Maryland district CSV schema")
    rows, keys = [], set()
    for row in reader:
        if None in row or any(row.get(c) is None for c in required):
            raise ValueError("Malformed CSV row")
        key = tuple(
            row[c] for c in ("County", "Office Name", "Office District", "Candidate Name", "Party")
        )
        if key in keys:
            raise ValueError("Duplicate county/contest/candidate row")
        keys.add(key)
        votes = {c: count(row[c]) for c in MD_COLUMNS}
        rows.append(
            {
                "county_code": row["County"],
                "county_name": row["County Name"],
                "contest": row["Office Name"],
                "office_district": row["Office District"],
                "candidate": row["Candidate Name"],
                "party": row["Party"],
                "district_votes": votes,
                "district_sum": sum(votes.values()),
            }
        )
    if not rows:
        raise ValueError("Empty result payload")
    return rows


def maryland_governor_html(body):
    """Parse only tables with the observed vote-mode headers; reject inconsistent totals."""
    soup = BeautifulSoup(body, "html.parser")
    rows = []
    headers = [
        "Name",
        "Party",
        "Early Voting",
        "Election Day",
        "Mail-In Ballot",
        "Provisional",
        "Total",
        "Percentage",
    ]
    for table in soup.find_all("table"):
        matched = False
        for tr in table.find_all("tr"):
            cells = [
                c.get_text(" ", strip=True) for c in tr.find_all(["td", "th"], recursive=False)
            ]
            if cells == headers:
                matched = True
                continue
            if not matched or len(cells) != len(headers) or cells[0] == "Totals":
                continue
            modes = dict(zip(headers[2:6], map(count, cells[2:6])))
            total = count(cells[6])
            if sum(modes.values()) != total:
                raise ValueError("Vote-mode sum does not match total")
            rows.append(
                {"candidate": cells[0], "party": cells[1], "mode_votes": modes, "total": total}
            )
    if not rows:
        raise ValueError("No supported vote tables")
    return rows


def reconcile_maryland_governor(html_rows, csv_rows):
    """Compare statewide Democratic candidate totals only; never sum counties with state."""
    statewide = {
        r["candidate"]: r["district_sum"]
        for r in csv_rows
        if r["county_code"] == "00"
        and r["contest"] == "Governor / Lt. Governor"
        and r["party"] == "DEM"
    }
    observed = {r["candidate"]: r["total"] for r in html_rows if r["party"] == "Democratic"}
    if not statewide or statewide.keys() != observed.keys():
        raise ValueError("Candidate context mismatch")
    if statewide != observed:
        raise ValueError("HTML/CSV vote totals disagree")
    return {
        "state": "MD",
        "contest": "Governor / Lt. Governor",
        "party": "DEM",
        "matched_candidates": len(observed),
        "matched_votes": sum(observed.values()),
        "verification_status": "historical_payload_crosschecked",
        "live_coverage": False,
        "served_jurisdiction_verified": False,
    }
