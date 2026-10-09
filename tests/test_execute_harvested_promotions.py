from scripts.execute_harvested_promotions import discover_artifact, parser_for_artifact


def test_parser_for_structured_artifacts():
    assert parser_for_artifact("https://x.gov/results.json")[1].endswith("parse_generic_results_json")
    assert parser_for_artifact("https://x.gov/results.csv")[1].endswith("parse_generic_precinct_csv")
    assert parser_for_artifact("https://x.gov/results.xlsx")[1].endswith("parse_generic_precinct_excel")
    assert parser_for_artifact("https://x.gov/detail.xml")[1].endswith("parse_clarity_like_xml")


def test_vendor_discovery_selects_json_over_zip():
    row={
        "source_url":"https://x.gov/election/",
        "execution_route":"election_data_grabber.adapters.vendor_structured:discover_vendor_artifacts",
    }
    body=b'<a href="archive.zip">Zip</a><script>fetch("/api/results.json")</script>'
    assert discover_artifact(row,body)=="https://x.gov/api/results.json"


def test_extensionless_excel_artifact_is_not_crashable():
    family,parser=parser_for_artifact("https://x.gov/download")
    assert family==""
    assert parser==""


def test_parser_exception_becomes_residual(monkeypatch):
    import scripts.execute_harvested_promotions as mod
    monkeypatch.setattr(mod,"fetch_body",lambda url,timeout:(b"not-an-xlsx",""))
    monkeypatch.setattr(
        mod,
        "execute_supported_body",
        lambda *args,**kwargs: (_ for _ in ()).throw(ValueError("bad workbook")),
    )
    rows=mod.execute_promotions([{
        "state":"AA",
        "source_url":"https://x.gov/results.xlsx",
        "promoted_family":"tabular_download",
        "execution_route":"election_data_grabber.adapters.generic_excel:parse_generic_precinct_excel",
        "promotion_action":"execute_now",
    }])
    assert rows[0]["execution_stage"]=="discovered"
    assert rows[0]["failure_class"]=="parser_exception:ValueError"


def test_bad_zip_parser_exception_becomes_residual(monkeypatch):
    import zipfile
    import scripts.execute_harvested_promotions as mod
    monkeypatch.setattr(mod,"fetch_body",lambda url,timeout:(b"not-an-xlsx",""))
    monkeypatch.setattr(
        mod,
        "execute_supported_body",
        lambda *args,**kwargs: (_ for _ in ()).throw(zipfile.BadZipFile("bad workbook")),
    )
    rows=mod.execute_promotions([{
        "state":"AA",
        "source_url":"https://x.gov/results.xlsx",
        "promoted_family":"tabular_download",
        "execution_route":"election_data_grabber.adapters.generic_excel:parse_generic_precinct_excel",
        "promotion_action":"execute_now",
    }])
    assert rows[0]["failure_class"]=="parser_exception:BadZipFile"


def test_xml_parse_exception_becomes_residual(monkeypatch):
    import xml.etree.ElementTree as ET
    import scripts.execute_harvested_promotions as mod
    monkeypatch.setattr(mod,"fetch_body",lambda url,timeout:(b"<bad xml>",""))
    monkeypatch.setattr(
        mod,
        "execute_supported_body",
        lambda *args,**kwargs: (_ for _ in ()).throw(ET.ParseError("bad xml")),
    )
    rows=mod.execute_promotions([{
        "state":"AA",
        "source_url":"https://x.gov/results.xml",
        "promoted_family":"structured_xml",
        "execution_route":"election_data_grabber.adapters.clarity_xml:parse_clarity_like_xml",
        "promotion_action":"execute_now",
    }])
    assert rows[0]["failure_class"]=="parser_exception:ParseError"


def test_html_payload_mismatch_becomes_landing_residual(monkeypatch):
    import scripts.execute_harvested_promotions as mod
    monkeypatch.setattr(mod,"fetch_body",lambda url,timeout:(b"<html>not json</html>",""))
    rows=mod.execute_promotions([{
        "state":"AA",
        "source_url":"https://x.gov/results.json",
        "promoted_family":"structured_json",
        "execution_route":"election_data_grabber.adapters.generic_json:parse_generic_results_json",
        "promotion_action":"execute_now",
    }])
    assert rows[0]["failure_class"]=="landing_page_no_structured_artifact"


def test_payload_format_reroutes_to_matching_parser(monkeypatch):
    import scripts.execute_harvested_promotions as mod
    seen={}
    monkeypatch.setattr(mod,"fetch_body",lambda url,timeout:(b'{"reporting_units":[]}',""))
    class Evidence:
        observations=[]
        snapshot_sha256="x"
        parser="election_data_grabber.adapters.generic_json:parse_generic_results_json"
        source_url="https://x.gov/results.xlsx"
        access_family="structured_json"
        smallest_observed_unit="unknown"
        vote_modes_preserved=False
    def fake_execute(manifest, body, **kwargs):
        seen.update(manifest)
        return Evidence()
    monkeypatch.setattr(mod,"execute_supported_body",fake_execute)
    monkeypatch.setattr(mod,"maturity_row",lambda evidence:{
        "state":"AA","result_url":seen["result_url"],"access_family":seen["access_family"],
        "parser":seen["parser"],"execution_stage":"normalized","observation_count":"0",
        "smallest_observed_unit":"unknown","vote_modes_preserved":"","failure_class":"",
        "snapshot_sha256":"x",
    })
    rows=mod.execute_promotions([{
        "state":"AA",
        "source_url":"https://x.gov/results.xlsx",
        "promoted_family":"tabular_download",
        "execution_route":"election_data_grabber.adapters.generic_excel:parse_generic_precinct_excel",
        "promotion_action":"execute_now",
    }])
    assert seen["access_family"]=="structured_json"
    assert seen["parser"]=="election_data_grabber.adapters.generic_json:parse_generic_results_json"
    assert rows[0]["failure_class"]==""


def test_markup_mismatch_discovers_and_executes_artifact(monkeypatch):
    import scripts.execute_harvested_promotions as mod
    landing=b'<html><a href="/downloads/results.csv">results</a></html>'
    calls=[]
    def fake_fetch(url,timeout):
        calls.append(url)
        if url.endswith("results.xlsx"):
            return landing,""
        if url.endswith("results.csv"):
            return b"precinct,office,candidate,votes\nP1,Mayor,A,5\n",""
        raise AssertionError(url)
    monkeypatch.setattr(mod,"fetch_body",fake_fetch)
    rows=mod.execute_promotions([{
        "state":"AA",
        "source_url":"https://x.gov/results.xlsx",
        "promoted_family":"tabular_download",
        "execution_route":"election_data_grabber.adapters.generic_excel:parse_generic_precinct_excel",
        "promotion_action":"execute_now",
    }])
    assert calls==["https://x.gov/results.xlsx","https://x.gov/downloads/results.csv"]
    assert rows[0]["execution_stage"] in {"normalized","replay_tested","refresh_verified"}

def test_markup_mismatch_without_artifact_is_residual(monkeypatch):
    import scripts.execute_harvested_promotions as mod
    monkeypatch.setattr(mod,"fetch_body",lambda url,timeout:(b"<html>No downloads here</html>",""))
    rows=mod.execute_promotions([{
        "state":"AA",
        "source_url":"https://x.gov/results.json",
        "promoted_family":"structured_json",
        "execution_route":"election_data_grabber.adapters.generic_json:parse_generic_results_json",
        "promotion_action":"execute_now",
    }])
    assert rows[0]["failure_class"]=="landing_page_no_structured_artifact"


def test_html_landing_mismatch_discovers_and_executes_artifact(monkeypatch):
    import scripts.execute_harvested_promotions as mod
    calls=[]
    landing=b'<html><a href="/downloads/results.csv">results</a></html>'
    csv=b"precinct,contest,candidate,votes\nP1,Mayor,Alice,3\n"
    def fake_fetch(url,timeout):
        calls.append(url)
        return (csv,"") if url.endswith("results.csv") else (landing,"")
    monkeypatch.setattr(mod,"fetch_body",fake_fetch)
    rows=mod.execute_promotions([{
        "state":"AA",
        "source_url":"https://x.gov/results.xlsx",
        "promoted_family":"tabular_download",
        "execution_route":"election_data_grabber.adapters.generic_excel:parse_generic_precinct_excel",
        "promotion_action":"execute_now",
    }])
    assert calls==["https://x.gov/results.xlsx","https://x.gov/downloads/results.csv"]
    assert rows[0]["failure_class"]==""
    assert rows[0]["execution_stage"] in {"normalized","replay_tested"}


def test_html_landing_mismatch_without_artifact_is_residual(monkeypatch):
    import scripts.execute_harvested_promotions as mod
    monkeypatch.setattr(mod,"fetch_body",lambda url,timeout:(b"<html><body>No exports</body></html>",""))
    rows=mod.execute_promotions([{
        "state":"AA",
        "source_url":"https://x.gov/results.json",
        "promoted_family":"structured_json",
        "execution_route":"election_data_grabber.adapters.generic_json:parse_generic_results_json",
        "promotion_action":"execute_now",
    }])
    assert rows[0]["failure_class"]=="landing_page_no_structured_artifact"


import pytest


@pytest.mark.parametrize("payload", [
    b'[{"reporting_units": []}]',
    b'{"results": []}',
    b'{"reporting_units": {}}',
    b'{"reporting_units": [null]}',
])
def test_unsupported_json_schema_becomes_residual(monkeypatch, payload):
    import scripts.execute_harvested_promotions as mod

    monkeypatch.setattr(mod, "fetch_body", lambda url, timeout: (payload, ""))
    rows = mod.execute_promotions([{
        "state": "AA",
        "source_url": "https://x.gov/results.json",
        "promoted_family": "structured_json",
        "execution_route": "election_data_grabber.adapters.generic_json:parse_generic_results_json",
        "promotion_action": "execute_now",
    }])
    assert len(rows) == 1
    assert rows[0]["execution_stage"] == "parser_selected"
    assert rows[0]["failure_class"] == "unsupported_json_schema"
    assert rows[0]["observation_count"] == "0"


def test_generic_json_contract_still_executes(monkeypatch):
    import scripts.execute_harvested_promotions as mod

    body = (
        b'{"reporting_units": [{"id": "P1", "name": "Precinct 1", '
        b'"contests": [{"name": "Mayor", "choices": [{"name": "Alice", "votes": 7}]}]}]}'
    )
    monkeypatch.setattr(mod, "fetch_body", lambda url, timeout: (body, ""))
    rows = mod.execute_promotions([{
        "state": "MI",
        "source_url": "https://x.gov/results.json",
        "promoted_family": "structured_json",
        "execution_route": "election_data_grabber.adapters.generic_json:parse_generic_results_json",
        "promotion_action": "execute_now",
    }])
    assert rows[0]["execution_stage"] == "replay_tested"
    assert rows[0]["observation_count"] == "1"
    assert not rows[0]["failure_class"]
