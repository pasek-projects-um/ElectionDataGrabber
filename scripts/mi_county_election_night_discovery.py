from __future__ import annotations
import csv
import re
from pathlib import Path
from urllib.parse import urljoin
import httpx
from bs4 import BeautifulSoup

TERMS=re.compile(r"(election.?results?|unofficial|results?|enhancedvoting|electionreporting|clarity|scytl|precinct)",re.I)

def discover(body: bytes, base: str):
    soup=BeautifulSoup(body,"html.parser")
    out=[]
    for a in soup.find_all("a",href=True):
        label=" ".join(a.stripped_strings)
        url=urljoin(base,str(a["href"]))
        if TERMS.search(label+" "+url):
            out.append((url,label))
    return out

def main():
    authorities={}
    with Path("registry/mi_county_authorities.csv").open(encoding="utf-8-sig") as f:
        for r in csv.DictReader(f): authorities[r["county"]]=r["authority_url"]
    rows=[]
    with httpx.Client(timeout=12,follow_redirects=True,headers={"User-Agent":"ElectionDataGrabber/0.1 (+academic election research)"}) as client:
        for county,url in authorities.items():
            status="unresolved"; resolved=""; candidates=[]
            try:
                r=client.get(url); r.raise_for_status(); resolved=str(r.url)
                candidates=discover(r.content,resolved)
                status="candidate_links_found" if candidates else "authority_reachable_no_result_link"
            except Exception as exc:
                status=f"authority_fetch_failed:{type(exc).__name__}"
            rows.append({"county":county,"authority_url":url,"resolved_url":resolved,"discovery_status":status,
                         "candidate_count":len(candidates),"candidate_urls":" | ".join(x[0] for x in candidates[:5])})
            print(county,status,len(candidates))
    Path("audit").mkdir(exist_ok=True)
    with Path("audit/mi-county-election-night-discovery.csv").open("w",newline="",encoding="utf-8") as f:
        w=csv.DictWriter(f,fieldnames=rows[0].keys());w.writeheader();w.writerows(rows)

if __name__=="__main__": main()
