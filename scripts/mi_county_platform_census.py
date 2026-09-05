"""Michigan county election-platform census.

Enumerates all 83 counties from Census Gazetteer input, then discovers and
fingerprints official election-result links.  Input authority URLs are kept in
CSV so discoveries can be reviewed and rerun without code changes.
"""
from __future__ import annotations
import argparse, csv, json
from pathlib import Path
from election_data_grabber.discovery import discover_result_links

FIELDS=["county_geoid","county","authority_url","result_url","label","platform","status","error"]

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--counties",type=Path,default=Path("registry/us_counties_2025.csv"))
    ap.add_argument("--authorities",type=Path,default=Path("registry/mi_county_authorities.csv"))
    ap.add_argument("--out",type=Path,default=Path("registry/mi_county_platform_census.csv"))
    args=ap.parse_args()
    authorities={}
    if args.authorities.exists():
        with args.authorities.open(encoding="utf-8-sig") as f:
            authorities={r["county"].strip().lower():r["authority_url"].strip() for r in csv.DictReader(f)}
    with args.counties.open(encoding="utf-8-sig") as f:
        counties=[r for r in csv.DictReader(f) if r["USPS"]=="MI"]
    rows=[]
    for c in counties:
        county=c["NAME"].removesuffix(" County")
        authority=authorities.get(county.lower(),"")
        if not authority:
            rows.append(dict(county_geoid=c["GEOID"],county=county,authority_url="",result_url="",label="",platform="",status="authority_missing",error=""))
            continue
        try:
            links=discover_result_links(authority)
            if not links:
                rows.append(dict(county_geoid=c["GEOID"],county=county,authority_url=authority,result_url="",label="",platform="",status="no_result_link_found",error=""))
            for x in links:
                rows.append(dict(county_geoid=c["GEOID"],county=county,authority_url=authority,result_url=x.url,label=x.label,platform=x.platform or "unknown",status="candidate",error=""))
        except Exception as exc:
            rows.append(dict(county_geoid=c["GEOID"],county=county,authority_url=authority,result_url="",label="",platform="",status="fetch_error",error=type(exc).__name__))
    args.out.parent.mkdir(parents=True,exist_ok=True)
    with args.out.open("w",newline="",encoding="utf-8") as f:
        w=csv.DictWriter(f,fieldnames=FIELDS);w.writeheader();w.writerows(rows)
    print(json.dumps({"counties":len(counties),"rows":len(rows),"output":str(args.out)}))

if __name__=="__main__": main()
