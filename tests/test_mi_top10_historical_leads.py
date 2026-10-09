import httpx
from scripts.mi_top10_election_night_fingerprint import scan, export, clean_url, read_leads


class FakeClient:
    def __init__(self, responses):
        self.responses=responses
        self.calls=[]
    def get(self,url):
        self.calls.append(url)
        result=self.responses[url]
        if isinstance(result,Exception): raise result
        return result


def response(url,text):
    return httpx.Response(200,text=text,request=httpx.Request("GET",url))


def test_historical_lead_survives_authority_outage():
    seed="https://county.example/elections"
    vendor="https://app.enhancedvoting.com/results/public/county/primary"
    bad=httpx.ConnectError("down",request=httpx.Request("GET",seed))
    client=FakeClient({seed:bad,vendor:response(vendor,"Election Results")})
    rows=scan({"Berrien":seed},[{"county":"Berrien","url":vendor,"platform_family":"enhanced_voting"}],client=client)
    assert len(rows)==2
    assert rows[0]["probe_status"]=="unavailable"
    assert rows[1]["discovery_origin"]=="historical_lead"
    assert rows[1]["probe_status"]=="reachable"
    assert vendor in client.calls


def test_relative_result_links_resolve_and_probe():
    seed="https://county.example/elections/index.html"
    child="https://county.example/elections/results.html"
    client=FakeClient({seed:response(seed,'<a href="results.html">Results</a>'),child:response(child,"precinct votes")})
    rows=scan({"Kent":seed},client=client)
    assert [row["url"] for row in rows]==[seed,child]
    assert rows[1]["discovery_origin"]=="current_link"


def test_invalid_and_cross_county_historical_leads_are_not_probed():
    seed="https://county.example/"
    client=FakeClient({seed:response(seed,"")})
    rows=scan({"Berrien":seed},[
        {"county":"Kent","url":"https://app.enhancedvoting.com/results/public/other","platform_family":"enhanced_voting"},
        {"county":"Berrien","url":"javascript:alert(1)","platform_family":"enhanced_voting"},
    ],client=client)
    assert len(rows)==1
    assert clean_url("javascript:alert(1)") is None


def test_export_counts_failures_separately(tmp_path):
    seed="https://county.example/"
    err=httpx.TimeoutException("timeout",request=httpx.Request("GET",seed))
    rows=scan({"Berrien":seed},client=FakeClient({seed:err}))
    summary=export(rows,tmp_path)
    assert summary["unavailable"]==1
    assert summary["families"]["fetch_failed"]==1
