from pathlib import Path
from scripts.build_harvested_source_execution_queue import classify_family, source_candidates


def test_clarity_urls_are_classified_to_clarity_adapter():
    family,parser=classify_family("https://results.enr.clarityelections.com/AR/122502/web.345435/#/reporting")
    assert family=="clarity"
    assert parser=="clarity"


def test_results_portal_requires_fingerprint_before_parser_promotion():
    family,parser=classify_family("https://results.sos.nd.gov/Default.aspx")
    assert family=="results_portal"
    assert parser==""


def test_queue_covers_all_states_and_dc():
    root=Path(__file__).resolve().parents[1]
    rows=source_candidates(root)
    assert len({r["state"] for r in rows})==51
    assert all(r["verification_status"]=="candidate" for r in rows)


def test_existing_adapter_families_are_promoted_to_adapter_candidate():
    root=Path(__file__).resolve().parents[1]
    rows=source_candidates(root)
    clarity=[r for r in rows if r["parser_family"]=="clarity"]
    assert clarity
    assert all(r["execution_stage"]=="adapter_candidate" for r in clarity)
