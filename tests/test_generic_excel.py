from datetime import datetime, timezone
import io

from openpyxl import Workbook

from election_data_grabber.adapters.generic_excel import parse_generic_precinct_excel


def _xlsx_bytes(rows):
    wb = Workbook()
    ws = wb.active
    for row in rows:
        ws.append(row)
    buf = io.BytesIO()
    wb.save(buf)
    wb.close()
    return buf.getvalue()


def test_xlsx_reuses_generic_csv_normalizer():
    body = _xlsx_bytes([
        ["metadata", "ignored"],
        ["precinct", "office", "candidate", "total"],
        ["P1", "Mayor", "Alice", 12],
    ])
    out = parse_generic_precinct_excel(
        body,
        filename="results.xlsx",
        election_id="e1",
        jurisdiction_id="us:me:test",
        source_id="s1",
        fetched_at=datetime.now(timezone.utc),
    )
    assert len(out) == 1
    assert out[0].reporting_unit_name == "P1"
    assert out[0].votes == 12


def test_xlsx_without_recognized_header_returns_empty():
    body = _xlsx_bytes([["foo", "bar"], ["1", "2"]])
    out = parse_generic_precinct_excel(
        body,
        filename="results.xlsx",
        election_id="e1",
        jurisdiction_id="us:me:test",
        source_id="s1",
        fetched_at=datetime.now(timezone.utc),
    )
    assert out == []
