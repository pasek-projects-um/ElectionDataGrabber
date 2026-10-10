from pathlib import Path

import pytest

from election_data_grabber.discovery_payloads import (
    count,
    maryland_congressional_csv,
    maryland_governor_html,
    reconcile_maryland_governor,
)

FIXTURES = Path(__file__).parent / "fixtures/dashboard_discovery"


def observed():
    return (
        maryland_governor_html((FIXTURES / "maryland-governor-2026.html").read_text()),
        maryland_congressional_csv((FIXTURES / "maryland-district-2026.csv").read_text()),
    )


def test_observed_maryland_modes_and_districts_reconcile_without_double_counting():
    html, csv = observed()
    assert len(html) == 11
    assert len(csv) == 4  # state and Allegany rows coexist; only state participates
    result = reconcile_maryland_governor(html, csv)
    assert result["matched_candidates"] == 2
    assert result["matched_votes"] == 633080
    assert result["verification_status"] == "historical_payload_crosschecked"
    assert result["live_coverage"] is False
    assert result["served_jurisdiction_verified"] is False


def test_mismatch_and_missing_candidate_rejected():
    html, csv = observed()
    csv[0]["district_sum"] += 1
    with pytest.raises(ValueError, match="disagree"):
        reconcile_maryland_governor(html, csv)
    with pytest.raises(ValueError, match="context mismatch"):
        reconcile_maryland_governor(html, [])


def test_bad_csv_and_duplicate_rows_rejected():
    text = (FIXTURES / "maryland-district-2026.csv").read_text()
    with pytest.raises(ValueError, match="Duplicate"):
        maryland_congressional_csv(text + text.splitlines()[1] + "\n")
    with pytest.raises(ValueError, match="schema"):
        maryland_congressional_csv("name,votes\nA,3\n")
    with pytest.raises(ValueError, match="Invalid vote"):
        maryland_congressional_csv(text.replace("8791", "NR", 1))


def test_inconsistent_html_and_shells_rejected():
    text = (FIXTURES / "maryland-governor-2026.html").read_text()
    with pytest.raises(ValueError, match="sum"):
        maryland_governor_html(text.replace("74,312", "74,313", 1))
    with pytest.raises(ValueError, match="No supported"):
        maryland_governor_html("<app-root>Election Results 2026</app-root>")


@pytest.mark.parametrize("value", ["", "NR", "-1", "1.2", "12,34", "true"])
def test_missing_and_noninteger_counts_are_not_zero(value):
    with pytest.raises(ValueError):
        count(value)


def test_official_totals_must_match_candidate_sums_for_each_mode():
    text = (FIXTURES / "maryland-governor-2026.html").read_text()
    # Preserve the total-row arithmetic but shift one vote between modes.
    text = text.replace("130,346", "130,347").replace("238,986", "238,985")
    with pytest.raises(ValueError, match="Candidate sums"):
        maryland_governor_html(text)


def test_duplicate_html_candidate_cannot_be_hidden_by_reconciliation():
    from bs4 import BeautifulSoup

    soup = BeautifulSoup((FIXTURES / "maryland-governor-2026.html").read_text(), "html.parser")
    candidate = soup.find("tbody").find("tr")
    candidate.insert_after(BeautifulSoup(str(candidate), "html.parser").find("tr"))
    with pytest.raises(ValueError, match="Duplicate candidate"):
        maryland_governor_html(str(soup))


@pytest.mark.parametrize("source", ["html", "csv"])
def test_reconciliation_rejects_duplicate_preparsed_candidates(source):
    html, csv = observed()
    selected = html if source == "html" else csv
    selected.append(dict(selected[0]))
    with pytest.raises(ValueError, match="Duplicate candidate"):
        reconcile_maryland_governor(html, csv)


@pytest.mark.parametrize("fault", ["missing_total", "duplicate_total", "short_row"])
def test_recognized_vote_tables_reject_incomplete_structure(fault):
    from bs4 import BeautifulSoup

    soup = BeautifulSoup((FIXTURES / "maryland-governor-2026.html").read_text(), "html.parser")
    table = soup.find("table")
    total = table.find_all("tr")[-1]
    if fault == "missing_total":
        total.decompose()
    elif fault == "duplicate_total":
        total.insert_after(BeautifulSoup(str(total), "html.parser").find("tr"))
    else:
        table.find("tbody").find("td").decompose()
    with pytest.raises(ValueError, match="Missing|Duplicate|Malformed"):
        maryland_governor_html(str(soup))
