from __future__ import annotations
"""Election-cycle-aware fingerprints with retained vendor leads.

Historical URLs are leads, never counted as currently active without a successful probe.
"""
import argparse
import csv
import json
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin, urlparse, urldefrag
import httpx

TARGETS={"Berrien","Eaton","Alpena","Newaygo","Schoolcraft","Washtenaw","Kent","Clinton","Cass","Lenawee"}
HOST_FAMILIES=[
 ("enhanced_voting",re.compile(r"enhancedvoting",re.I)),
 ("election_reporting",re.compile(r"electionreporting",re.I)),
 ("clarity",re.compile(r"clarity|enr\\.clarity",re.I)),
 ("scytl",re.compile(r"scytl",re.I)),
 ("civicplus",re.compile(r"civicplus|civicengage",re.I)),
]
DATA_HINT=re.compile(r"(\\.json(?:\\?|$)|\\.csv(?:\\?|$)|\\.xml(?:\\?|$)|api/|results?|precinct|reporting)",re.I)
LINK_HINT=re.compile(r"(result|election|enhanced|clarity|report)",re.I)
LINK_RE=re.compile(r'''href\\s*=\\s*["']([^"']+)["']''',re.I)
FIELDS=("county","url","host","platform_family","content_type","data_hints","precinct_token","reporting_token","timestamp_token","vote_mode_token","discovery_origin","probe_status","http_status","error_class")
VENDOR_FAMILIES={"enhanced_voting","election_reporting","clarity","scytl"}
HEADERS={"User-Agent":"ElectionDataGrabber/0.1 (+academic election research)"}

def family(url,body=""):
    blob=url+" "+body[:200000]
    for name,pattern in HOST_FAMILIES:
        if pattern.search(blob): return name
    return "unknown_web"

def hints(body,base_host):
    urls=set(re.findall(r'''https?://[^\\s'"<>]+''',body))
    rel=re.findall(r'''["']([^"']+(?:\\.json|\\.csv|\\.xml|api/[^"']+))''',body,re.I)
    urls.update(rel)
    return sorted(u for u in urls if DATA_HINT.search(u))[:30]

def clean_url(raw,base=""):
    if raw.strip().lower().startswith(("javascript:","data:","mailto:")): return None
    url=urldefrag(urljoin(base,raw.strip()))[0]
    parsed=urlparse(url)
    if parsed.scheme not in ("http","https") or not parsed.hostname or parsed.username or parsed.password:
        return None
    return url

def read_leads(path):
    if not path or not Path(path).exists(): return []
    with Path(path).open(encoding="utf-8-sig",newline="") as stream:
        return [row for row in csv.DictReader(stream) if row.get("county") in TARGETS and clean_url(row.get("url",""))]

def _record(county,url,response,origin):
    text=response.text
    final=str(response.url)
    return {"county":county,"url":final,"host":urlparse(final).hostname or "",
        "platform_family":family(final,text),"content_type":response.headers.get("content-type",""),
        "data_hints":" | ".join(hints(text,urlparse(final).hostname or "")),
        "precinct_token":bool(re.search(r"precinct",text,re.I)),
        "reporting_token":bool(re.search(r"(precincts? reporting|reporting units?|percent reporting)",text,re.I)),
        "timestamp_token":bool(re.search(r"(last updated|updated at|timestamp)",text,re.I)),
        "vote_mode_token":bool(re.search(r"(absentee|early voting|election day|AVCB|provisional)",text,re.I)),
        "discovery_origin":origin,"probe_status":"reachable","http_status":response.status_code,"error_class":""}

def _failure(county,url,origin,exc):
    status=exc.response.status_code if isinstance(exc,httpx.HTTPStatusError) else ""
    return {"county":county,"url":url,"host":urlparse(url).hostname or "",
        "platform_family":"fetch_failed","content_type":"","data_hints":"",
        "precinct_token":False,"reporting_token":False,"timestamp_token":False,"vote_mode_token":False,
        "discovery_origin":origin,"probe_status":"unavailable","http_status":status,
        "error_class":type(exc).__name__}

def scan(authorities,previous=(),client=None):
    """Probe county authority and retained leads independently, including after authority failures."""
    own_client=client is None
    if own_client: client=httpx.Client(timeout=15,follow_redirects=True,headers=HEADERS)
    try:
        known={}
        for row in previous:
            county=row.get("county")
            url=clean_url(row.get("url",""))
            if county in TARGETS and url and family(url)==row.get("platform_family") and row.get("platform_family") in VENDOR_FAMILIES:
                known[(county,url)]="historical_lead"
        output=[]
        for county,seed in authorities.items():
            candidates={}
            primary=clean_url(seed)
            if primary: candidates[primary]="authority"
            for (lead_county,url),origin in known.items():
                if lead_county==county and url!=primary: candidates[url]=origin
            if primary:
                try:
                    response=client.get(primary);response.raise_for_status()
                    output.append(_record(county,primary,response,"authority"))
                    for raw in LINK_RE.findall(response.text):
                        if not LINK_HINT.search(raw): continue
                        url=clean_url(raw,str(response.url))
                        if url and url not in candidates: candidates[url]="current_link"
                except httpx.HTTPError as exc:
                    output.append(_failure(county,primary,"authority",exc))
            for url,origin in candidates.items():
                if url==primary: continue
                try:
                    response=client.get(url);response.raise_for_status()
                    output.append(_record(county,url,response,origin))
                except httpx.HTTPError as exc:
                    output.append(_failure(county,url,origin,exc))
        return output
    finally:
        if own_client: client.close()

def export(rows,outdir):
    root=Path(outdir);root.mkdir(parents=True,exist_ok=True)
    with (root/"mi-top10-election-night-fingerprints.csv").open("w",newline="",encoding="utf-8") as stream:
        writer=csv.DictWriter(stream,fieldnames=FIELDS);writer.writeheader();writer.writerows(rows)
    counts=Counter(row["platform_family"] for row in rows)
    summary={"targets":len(TARGETS),"rows":len(rows),"families":dict(counts),
        "reachable":sum(row["probe_status"]=="reachable" for row in rows),
        "unavailable":sum(row["probe_status"]=="unavailable" for row in rows),
        "retained_leads_probed":sum(row["discovery_origin"]=="historical_lead" for row in rows)}
    (root/"mi-top10-election-night-summary.json").write_text(json.dumps(summary,indent=2,sort_keys=True))
    return summary

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--previous",default="",help="Previous fingerprint CSV (optional)")
    parser.add_argument("--output",default="audit")
    args=parser.parse_args()
    authorities={}
    with Path("registry/mi_county_authorities.csv").open(encoding="utf-8-sig",newline="") as stream:
        for row in csv.DictReader(stream):
            if row["county"] in TARGETS: authorities[row["county"]]=row["authority_url"]
    summary=export(scan(authorities,read_leads(args.previous)),args.output)
    print("SUMMARY",json.dumps(summary,sort_keys=True))

if __name__=="__main__": main()
