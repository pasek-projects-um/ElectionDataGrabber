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
