from election_data_grabber.adapters.tabulator_reports import profile_tabulator_report

def test_profiles_canvass_report_semantics():
    x=profile_tabulator_report("Canvass Results Report Precincts Reporting 9 of 9 Registered Voters Voters Cast Election Day Absentee Early Voting")
    assert x and x.precincts_reported==9 and x.precincts_total==9
    assert x.has_turnout
    assert set(x.vote_modes)=={"election day","absentee","early voting"}
