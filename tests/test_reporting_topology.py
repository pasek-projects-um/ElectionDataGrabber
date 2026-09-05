from election_data_grabber.reporting_topology import AdministrativePath, maine_reconciliation_keys

def test_maine_path_does_not_require_county_reporting_unit():
    path=AdministrativePath(state="ME",county="Cumberland",municipality="Portland",ward="Ward 2",precinct="2-1")
    assert maine_reconciliation_keys(path)==[
        ("state","ME"),("county","Cumberland"),("municipality","Portland"),
        ("ward","Ward 2"),("precinct","2-1")
    ]
