from scripts.audit_maine_end_to_end import audit_html, text_metrics
from election_data_grabber.artifact_auditor import AuditStatus

def test_text_metrics_find_reporting_units():
    units, contests, numeric = text_metrics("Ward 1 President Alice 123 Bob 99 Precinct 2 Governor 44")
    assert units >= 2
    assert contests >= 2
    assert numeric >= 3

def test_html_results_table_is_parseable_shape():
    html=b"""
    <html><table>
      <tr><th>Ward 1</th><th>Governor</th><th>Votes</th></tr>
      <tr><td>Ward 1</td><td>Alice</td><td>123</td></tr>
      <tr><td>Ward 1</td><td>Bob</td><td>99</td></tr>
    </table></html>
    """
    a=audit_html("https://example.gov/results", html)
    assert a.status == AuditStatus.PARSED
    assert a.reporting_units >= 1
    assert a.result_rows >= 2
