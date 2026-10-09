"""One bounded official municipality-roster pass for MA, VT and WI.

Candidate geography names are not election-night source verification.
If an official geography roster does not reconcile to the known denominator,
skip that state and describe the discrepancy rather than trimming rows.
"""
import csv
import re
from collections import Counter
from pathlib import Path
import httpx
from ingest_priority_state_rosters import FIELDS, append_unique

SOURCES = {
    "MA": ("https://services1.arcgis.com/hGdibHYSPO59RG1h/arcgis/rest/services/Massachusetts_Municipalities/FeatureServer/1/query", "TOWN", 351),
    "VT": ("https://services1.arcgis.com/BkFxaEFNwHqX3tAw/arcgis/rest/services/FS_VCGI_OPENDATA_Boundary_BNDHASH_poly_towns_SP_v1/FeatureServer/0/query", "TOWNNAMEMC", 247),
}
# WI clerk directory requires a verified export of clerk jurisdictions and
# jurisdiction types; statewide counties and incorporated municipalities must
# not be mixed or artificially truncated to a provisional 1,850.
WI_URL = "https://elections.wi.gov/clerks/directory"

def main():
    root=Path("registry")
    with (root/"us_primary_election_localities.csv").open(newline="",encoding="utf-8-sig") as f:
        rows=list(csv.DictReader(f))
    added=Counter()
    with httpx.Client(timeout=90,follow_redirects=True) as client:
        for state,(url,field,expected) in SOURCES.items():
            try:
                response=client.get(url,params={"where":"1=1","outFields":"*","returnGeometry":"false","f":"json","resultRecordCount":2000})
                response.raise_for_status()
                payload=response.json()
                if "error" in payload:
                    raise ValueError(str(payload["error"]))
                features=payload.get("features",[])
                names=sorted({str(x["attributes"].get(field,"")).strip() for x in features if x.get("attributes",{}).get(field)})
                print(f"{state} official GIS: {len(features)} features; {len(names)} names; sample attributes {features[0]['attributes'] if features else {}}")
                if len(names)!=expected:
                    print(f"{state} DEFERRED: GIS roster count {len(names)} != expected {expected}; sample names {names[:12]}; do not guess")
                    continue
                for name in names:
                    if append_unique(rows,state,name,"municipality",re.sub(r"[^a-z0-9]+","-",name.lower()),url):
                        added[state]+=1
            except (httpx.HTTPError,ValueError,KeyError) as exc:
                print(f"{state} DEFERRED: official GIS not usable ({type(exc).__name__}: {exc})")
        print(f"WI DEFERRED: no reconciled official clerk export fetched; provenance {WI_URL}")
    with (root/"us_primary_election_localities.csv").open("w",newline="",encoding="utf-8") as f:
        writer=csv.DictWriter(f,fieldnames=FIELDS);writer.writeheader();writer.writerows(rows)
    print("Three-state bounded import added:",dict(added),"total",sum(added.values()))

if __name__=="__main__":
    main()
