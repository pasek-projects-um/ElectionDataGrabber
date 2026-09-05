from __future__ import annotations
import csv, json, re
from collections import Counter
from pathlib import Path
from urllib.parse import urlparse
import httpx

TARGETS={"Berrien","Eaton","Alpena","Newaygo","Schoolcraft","Washtenaw","Kent","Clinton","Cass","Lenawee"}
HOST_FAMILIES=[
 ("enhanced_voting",re.compile(r"enhancedvoting",re.I)),
 ("election_reporting",re.compile(r"electionreporting",re.I)),
 ("clarity",re.compile(r"clarity|enr\.clarity",re.I)),
 ("scytl",re.compile(r"scytl",re.I)),
 ("civicplus",re.compile(r"civicplus|civicengage",re.I)),
]
DATA_HINT=re.compile(r"(\.json(?:\?|$)|\.csv(?:\?|$)|\.xml(?:\?|$)|api/|results?|precinct|reporting)",re.I)

def family(url,body=""):
    blob=url+" "+body[:200000]
    for name,p in HOST_FAMILIES:
        if p.search(blob): return name
    return "unknown_web"

def hints(body,base_host):
    urls=set(re.findall(r'https?://[^\s\'"<>]+',body))
    rel=re.findall(r'[\'"]([^\'"]+(?:\.json|\.csv|\.xml|api/[^\'"]+))',body,re.I)
    urls.update(rel)
    return sorted(u for u in urls if DATA_HINT.search(u))[:30]

def main():
    auth={}
    with Path("registry/mi_county_authorities.csv").open(encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            if r["county"] in TARGETS: auth[r["county"]]=r["authority_url"]
    out=[]
    with httpx.Client(timeout=15,follow_redirects=True,headers={"User-Agent":"ElectionDataGrabber/0.1 (+academic election research)"}) as c:
        for county,seed in auth.items():
            try:
                r=c.get(seed); r.raise_for_status()
                body=r.text
                links=re.findall(r'href=[\'"]([^\'"]+)[\'"]',body,re.I)
                candidates=[]
                for x in links:
                    if re.search(r"(result|election|enhanced|clarity|report)",x,re.I): candidates.append(x)
                probe=[str(r.url)]+candidates[:12]
                seen=set()
                for u in probe:
                    if u in seen: continue
                    seen.add(u)
                    try:
                        rr=c.get(u); rr.raise_for_status()
                        text=rr.text
                        out.append({"county":county,"url":str(rr.url),"host":urlparse(str(rr.url)).hostname or "",
                          "platform_family":family(str(rr.url),text),"content_type":rr.headers.get("content-type",""),
                          "data_hints":" | ".join(hints(text,urlparse(str(rr.url)).hostname or "")),
                          "precinct_token":bool(re.search(r"precinct",text,re.I)),
                          "reporting_token":bool(re.search(r"(precincts? reporting|reporting units?|percent reporting)",text,re.I)),
                          "timestamp_token":bool(re.search(r"(last updated|updated at|timestamp)",text,re.I)),
                          "vote_mode_token":bool(re.search(r"(absentee|early voting|election day|AVCB|provisional)",text,re.I))})
                    except Exception: pass
            except Exception as exc:
                out.append({"county":county,"url":seed,"host":"","platform_family":"fetch_failed","content_type":"",
                  "data_hints":"","precinct_token":False,"reporting_token":False,"timestamp_token":False,"vote_mode_token":False})
    Path("audit").mkdir(exist_ok=True)
    fields=list(out[0])
    with Path("audit/mi-top10-election-night-fingerprints.csv").open("w",newline="",encoding="utf-8") as f:
        w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(out)
    summary={"targets":len(TARGETS),"rows":len(out),"families":dict(Counter(x["platform_family"] for x in out))}
    Path("audit/mi-top10-election-night-summary.json").write_text(json.dumps(summary,indent=2,sort_keys=True))
    print("SUMMARY",json.dumps(summary,sort_keys=True))
if __name__=="__main__": main()
