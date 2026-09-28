from pathlib import Path
from scripts.build_harvested_source_execution_queue import classify_family, source_candidates


def test_clarity_urls_are_classified_to_clarity_adapter():
    family,parser=classify_family("https://results.enr.clarityelections.com/AR/122502/web.345435/#/reporting")
    assert family=="clarity"
    assert parser=="clarity"


def test_results_portal_gets_generic_html_fallback():
    family,parser=classify_family("https://results.sos.nd.gov/Default.aspx")
    assert family=="results_portal"
    assert parser=="generic_html"


def test_queue_covers_all_states_and_dc():
    root=Path(__file__).resolve().parents[1]
    rows=source_candidates(root)
    assert len({r["state"] for r in rows})==51
    assert all(r["verification_status"]=="candidate" for r in rows)
