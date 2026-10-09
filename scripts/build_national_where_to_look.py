from __future__ import annotations
"""Compile a nationwide 'where to look' inventory from existing evidence.

This is a candidate-location index, not a claim that every locality has a verified URL.
Missing local authorities remain explicit coverage gaps.
"""
import csv
import json
from collections import Counter
from pathlib import Path
from urllib.parse import urlsplit


FIELDS = ("jurisdiction_id","state","jurisdiction_level","jurisdiction_name","page_role",
          "url","evidence_registry","verification_status")


def build(root: Path):
    records = {}
    jurisdictions = {}

    def add(jid, state, level, name, role, url, source, status="candidate"):
        url = url.strip()
        if not url or urlsplit(url).scheme not in ("http","https") or not urlsplit(url).hostname:
            return
        key = (jid, role, url)
        records[key] = dict(zip(FIELDS, (jid,state,level,name,role,url,source,status)))

    def read(filename):
        with (root / filename).open(encoding="utf-8-sig",newline="") as stream:
            yield from csv.DictReader(stream)

    for row in read("us_primary_election_localities.csv"):
        jid = row["jurisdiction_id"]
        jurisdictions[jid] = (row["state"],row["jurisdiction_level"],row["canonical_name"])
        for field,role in (("final_evidence_url","historical_or_final_results"),
                           ("election_night_evidence_url","election_night_lead")):
            add(jid,row["state"],row["jurisdiction_level"],row["canonical_name"],role,
                row.get(field,""),"us_primary_election_localities.csv",
                row.get("assessment_status","candidate"))
    for row in read("us_state_central_authority_sources.csv"):
        state = row["state"]
        add(f"us:{state.lower()}",state,"state",state,"state_election_authority",
            row["central_authority_url"],"us_state_central_authority_sources.csv",row.get("status","candidate"))
    for state,filename,key in (("MI","mi_county_authorities.csv","county"),
                                ("OH","oh_county_authorities.csv","county"),
                                ("ME","me_locality_authorities.csv","locality")):
        for row in read(filename):
            name=row[key]
            county=row.get("county","")
            jid = f"us:{state.lower()}:{key}:{name.lower().replace(' ','-')}"
            if state=="ME" and county:
                jid += f":{county.lower().replace(' ','-')}"
            add(jid,state,key,name,"local_election_authority",row["authority_url"],filename)
    for row in read("sources.csv"):
        if row.get("official","").lower()!="true": continue
        state=row["state"]
        add(f"us:{state.lower()}:source:{row['source_id']}",state,"source",
            row["jurisdiction"],"official_source",row["url"],"sources.csv")
    for row in read("us_local_reporting_sources.csv"):
        state=row.get("state","")
        level=row.get("locality_type","unknown")
        name=row.get("locality_name","")
        jid=f"us:{state.lower()}:{level}:{name.lower().replace(' ','-')}"
        for field,role in (("authority_url","local_election_authority"),("results_url","results_lead")):
            for url in row.get(field,"").split("|"):
                add(jid,state,level,name,role,url,"us_local_reporting_sources.csv",row.get("status","candidate"))
    # Every locality must have a crawl entry point, even when its own office
    # has not yet been identified. State authorities are explicit fallbacks,
    # never mislabeled as verified locality sites.
    state_entries = {}
    for row in records.values():
        if row["page_role"] == "state_election_authority":
            state_entries.setdefault(row["state"], []).append(row["url"])
    direct = {row["jurisdiction_id"] for row in records.values()}
    for jid, (state, level, name) in jurisdictions.items():
        if jid in direct:
            continue
        for url in sorted(set(state_entries.get(state, [])))[:2]:
            add(jid, state, level, name, "state_directory_fallback", url,
                "us_state_central_authority_sources.csv", "fallback_unverified_for_locality")
    rows=sorted(records.values(),key=lambda x:(x["state"],x["jurisdiction_id"],x["page_role"],x["url"]))
    represented={row["jurisdiction_id"] for row in rows}
    gaps=[{"jurisdiction_id":jid,"state":s,"jurisdiction_level":level,"jurisdiction_name":name,
           "gap":"no_registered_local_url"}
          for jid,(s,level,name) in sorted(jurisdictions.items()) if jid not in represented]
    summary={"known_locality_jurisdictions":len(jurisdictions),
             "localities_without_registered_url":len(gaps),
             "localities_without_any_start":sum(g["gap"]=="no_starting_url" for g in gaps),
             "localities_using_state_fallback":sum(g["gap"]=="state_fallback_only" for g in gaps),
             "candidate_pages":len(rows),
             "states_with_candidates":len({row["state"] for row in rows}),
             "roles":dict(Counter(row["page_role"] for row in rows))}
    return rows,gaps,summary


def main():
    import argparse
    parser=argparse.ArgumentParser()
    parser.add_argument("--registry",default="registry")
    parser.add_argument("--output",default="audit")
    args=parser.parse_args()
    rows,gaps,summary=build(Path(args.registry))
    out=Path(args.output);out.mkdir(parents=True,exist_ok=True)
    for filename,data,fields in (
        ("national-where-to-look.csv",rows,FIELDS),
        ("national-where-to-look-gaps.csv",gaps,("jurisdiction_id","state","jurisdiction_level","jurisdiction_name","gap"))):
        with (out/filename).open("w",encoding="utf-8",newline="") as stream:
            writer=csv.DictWriter(stream,fieldnames=fields)
            writer.writeheader();writer.writerows(data)
    (out/"national-where-to-look-summary.json").write_text(json.dumps(summary,indent=2,sort_keys=True))
    print(json.dumps(summary,sort_keys=True))


if __name__=="__main__":
    main()
