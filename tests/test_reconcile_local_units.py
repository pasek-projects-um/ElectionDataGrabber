from scripts.reconcile_local_units import infer

def test_county_host_reconciles_high_confidence():
    r={"state":"IA","authority_url":"https://www.grundycountyiowa.gov/departments/auditor","status":"reached"}
    c=infer(r,"county")
    assert c is not None
    assert c.name_token=="grundy"
    assert c.jurisdiction_level=="county"

def test_generic_state_page_does_not_reconcile():
    r={"state":"AZ","authority_url":"https://azsos.gov/elections/candidates","status":"reached"}
    assert infer(r,"county") is None
