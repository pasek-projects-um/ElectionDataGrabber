import json
from datetime import datetime, timezone

from election_data_grabber.adapters.enhanced_voting import (
    discover_enhanced_voting_urls, parse_enhanced_voting_html,
)
from election_data_grabber.adapters.clarity import clarity_election_root, discover_clarity_urls
from election_data_grabber.adapters.civicplus import discover_civicplus_result_links


def test_enhanced_voting_embedded_json_normalizes_rows():
    payload={"props":{"pageProps":{"results":[
        {"precinctName":"Ward 1","contestName":"Mayor","candidateName":"Alice","party":"DEM","total":123,"absentee":50},
        {"precinctName":"Ward 1","contestName":"Mayor","candidateName":"Bob","party":"REP","total":100,"absentee":30},
    ]}}}
    html=f'<script id="__NEXT_DATA__" type="application/json">{json.dumps(payload)}</script>'.encode()
    rows=parse_enhanced_voting_html(
        html,election_id="e1",jurisdiction_id="j1",source_id="s1",
        fetched_at=datetime(2026,8,4,tzinfo=timezone.utc),
    )
    assert len(rows)==4
    assert {r.reporting_unit_name for r in rows}=={"Ward 1"}
    assert {r.choice_name for r in rows}=={"Alice","Bob"}
    assert all(r.ballot_order is None for r in rows)


def test_enhanced_voting_url_discovery():
    body=b'<a href="https://app.enhancedvoting.com/results/public/example/elections/2026">Results</a>'
    assert discover_enhanced_voting_urls(body)==[
        "https://app.enhancedvoting.com/results/public/example/elections/2026"
    ]


def test_clarity_root_and_discovery():
    url="https://results.enr.clarityelections.com/MI/Eaton/124075/web.345435/#/summary"
    assert clarity_election_root(url)=="https://results.enr.clarityelections.com/MI/Eaton/124075/"
    body=f'<a href="{url}">Official Results</a>'.encode()
    assert discover_clarity_urls(body)==[url]


def test_civicplus_delegates_to_vendor_and_documents():
    body=b"""
      <a href="https://app.enhancedvoting.com/results/public/a/elections/x">Election Results</a>
      <a href="https://results.enr.clarityelections.com/MI/X/123/">Unofficial Results</a>
      <a href="/DocumentCenter/View/9/results.pdf">Official Election Results PDF</a>
    """
    got=discover_civicplus_result_links(body,"https://county.gov/elections")
    assert {x.downstream_family for x in got}=={"enhanced_voting","clarity","document"}
