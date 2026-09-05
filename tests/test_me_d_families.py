from election_data_grabber.adapters.archive_discovery import discover_election_artifacts
from election_data_grabber.adapters.dynamic_documents import fingerprint_dynamic_document

def test_absentee_application_not_a_result():
    body=b'<a href="/absentee-ballot-application.pdf">Absentee Ballot Application</a>'
    assert discover_election_artifacts(body,"https://town.gov/elections/") == []

def test_dynamic_tyler_document_family_detected():
    assert fingerprint_dynamic_document("https://records.town.gov/Portico/Results/2024") == "tyler_portico"
