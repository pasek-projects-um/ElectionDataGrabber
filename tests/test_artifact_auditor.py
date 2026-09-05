from election_data_grabber.artifact_auditor import *

def test_parsed_reporting_units_are_a():
    a=ArtifactAudit("x",AuditStatus.PARSED,result_rows=20,reporting_units=4)
    assert provisional_portability(a)=="A"
    assert not needs_escalation(a)

def test_scanned_unreadable_artifact_escalates():
    a=ArtifactAudit("x",AuditStatus.UNREADABLE,has_text_layer=False)
    assert provisional_portability(a)=="E"
    assert needs_escalation(a)

def test_reconciliation_failure_escalates():
    a=ArtifactAudit("x",AuditStatus.PARSED,result_rows=10,reporting_units=2,reconciliation_error=.02)
    assert needs_escalation(a)
