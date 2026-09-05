from __future__ import annotations
import csv,json,re
from collections import Counter
from pathlib import Path
from urllib.parse import urljoin,urlparse
import httpx

RESULT_RE=re.compile(r"(election\s+results?|unofficial\s+results?|official\s+results?|statement\s+of\s+votes?|canvass|election\s+night|precinct\s+results?)",re.I)
PLATFORMS=[
 ("enhanced_voting",re.compile(r"enhancedvoting",re.I)),
 ("clarity",re.compile(r"clarityelections|election night reporting",re.I)),
 ("civicplus",re.compile(r"civicplus|civicengage|documentcenter",re.I)),
 ("scytl",re.compile(r"scytl",re.I)),
 ("electionware",re.compile(r"electionware",re.I)),
]
STATE_ENTRY={
 "WI":"https://elections.wi.gov/clerks/directory",
 "MA":"https://www.sec.state.ma.us/divisions/elections/local-officials/find-my-election-office.htm",
 "NH":"https://www.sos.nh.gov/elections",
 "VT":"https://sos.vermont.gov/elections/",
 "NJ":"https://www.nj.gov/state/elections/vote-county-election-officials.shtml",
 "VA":"https://www.elections.virginia.gov/localGR/",
 "LA":"https://www.sos.la.gov/ElectionsAndVoting/FindPublicOfficials/ClerksOfCourt/Pages/default.aspx",
 "MN":"https://www.sos.state.mn.us/elections-voting/find-county-election-office/",
 "RI":"https://elections.ri.gov/about-us/local-boards-canvassers",
 "MD":"https://elections.maryland.gov/about/county_boards.html",
 "MO":"https://www.sos.mo.gov/elections/goVoteMissouri/localelectionauthority",
 "AK":"https://www.elections.alaska.gov/",
 "HI":"https://elections.hawaii.gov/resources/county-election-divisions/",
 "OR":"https://sos.oregon.gov/elections/Pages/countyofficials.aspx",
 "NM":"https://www.sos.nm.gov/voting-and-elections/voter-information-portal/county-clerk-information/",
 "ND":"https://www.sos.nd.gov/elections/county-election-officials",
 "SC":"https://scvotes.gov/contact/county-voter-registration-election-offices/",
 "NY":"https://elections.ny.gov/county-boards-elections",
}
def platform(url,body):
    blob=url+" "+body[:200000]
    for n,p in PLATFORMS:
        if p.search(blob): return n
    if ".pdf" in url.lower(): return "pdf"
    return "unknown_web"

def main():
    out=[]
    with httpx.Client(timeout=20,follow_redirects=True,headers={"User-Agent":"ElectionDataGrabber/0.1 (+academic election research)"}) as c:
      for state,entry in STATE_ENTRY.items():
        try:
          r=c.get(entry); r.raise_for_status(); body=r.text
          links=re.findall(r'href=[\'"]([^\'"]+)[\'"]',body,re.I)
          officials=[]
          for href in links:
            u=urljoin(str(r.url),href)
            host=urlparse(u).hostname or ""
            if host and u not in officials and not u.startswith("mailto:"): officials.append(u)
          # Broad first pass: preserve official directory plus likely election/result links.
          candidates=[u for u in officials if RESULT_RE.search(u) or re.search(r"(county|clerk|election|vote)",u,re.I)][:120]
          if not candidates: candidates=officials[:40]
          out.append({"state":state,"locality_type":"state_directory","locality_name":"","authority_url":str(r.url),
            "results_url":"","source_scope":"directory","election_night_candidate":"","smallest_observed_unit":"",
            "vote_mode_detail":"","platform_family":platform(str(r.url),body),"status":"directory_reached",
            "discovered_from":entry,"notes":f"{len(candidates)} candidate links"})
          for u in candidates:
            try:
              rr=c.get(u); rr.raise_for_status(); text=rr.text
              result_links=[urljoin(str(rr.url),x) for x in re.findall(r'href=[\'"]([^\'"]+)[\'"]',text,re.I)
                            if RESULT_RE.search(x)]
              out.append({"state":state,"locality_type":"candidate_authority","locality_name":"",
                "authority_url":str(rr.url),"results_url":" | ".join(result_links[:10]),"source_scope":"local_candidate",
                "election_night_candidate":str(bool(re.search(r"election\s+night|unofficial",text,re.I))).lower(),
                "smallest_observed_unit":"precinct" if re.search(r"precinct",text,re.I) else "",
                "vote_mode_detail":"mode_labels_present" if re.search(r"absentee|early voting|vote by mail|provisional",text,re.I) else "",
                "platform_family":platform(str(rr.url),text),"status":"reached","discovered_from":str(r.url),"notes":""})
            except Exception: pass
        except Exception as exc:
          out.append({"state":state,"locality_type":"state_directory","locality_name":"","authority_url":entry,
            "results_url":"","source_scope":"directory","election_night_candidate":"","smallest_observed_unit":"",
            "vote_mode_detail":"","platform_family":"","status":"fetch_failed","discovered_from":entry,"notes":type(exc).__name__})
    Path("audit").mkdir(exist_ok=True)
    fields=["state","locality_type","locality_name","authority_url","results_url","source_scope","election_night_candidate","smallest_observed_unit","vote_mode_detail","platform_family","status","discovered_from","notes"]
    with Path("audit/us-local-reporting-source-sweep.csv").open("w",newline="",encoding="utf-8") as f:
      w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(out)
    summary={"rows":len(out),"states":len(STATE_ENTRY),"status":dict(Counter(x["status"] for x in out)),
             "platforms":dict(Counter(x["platform_family"] for x in out if x["platform_family"]))}
    Path("audit/us-local-reporting-source-summary.json").write_text(json.dumps(summary,indent=2,sort_keys=True))
    print("SUMMARY",json.dumps(summary,sort_keys=True))
if __name__=="__main__": main()
