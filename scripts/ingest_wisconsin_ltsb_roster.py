"""One-pass Wisconsin named municipality enumeration from WI LTSB 2026 CTV GIS.

This populates only source-backed municipality candidates; it never turns the
provisional 1850 administrative count into fictitious verified authorities.
"""
import csv
import re
from pathlib import Path
from collections import Counter
import httpx
from ingest_priority_state_rosters import FIELDS, append_unique

BASE="https://services1.arcgis.com/FDsAtKBk8Hy4cAH0/ArcGIS/rest/services/WI_Cities_Towns_and_Villages_Current/FeatureServer/0"
DIRECTORY="https://elections.wi.gov/clerks/directory"
EXPECTED=1850

def main():
    root=Path("registry")
    with (root/"us_primary_election_localities.csv").open(newline="",encoding="utf-8-sig") as f:
        rows=list(csv.DictReader(f))
    with httpx.Client(timeout=90,follow_redirects=True) as client:
        m=client.get(BASE,params={"f":"json"});m.raise_for_status()
        meta=m.json()
        if "error" in meta:
            raise ValueError(f"WI feature layer: {meta['error']}")
        names=[(f["name"],f["type"]) for f in meta.get("fields",[])]
        print("WI fields", names)
        cnt=client.get(BASE+"/query",params={"f":"json","where":"1=1","returnCountOnly":"true"});cnt.raise_for_status()
        count=cnt.json().get("count")
        if not isinstance(count,int) or not 1750 <= count <= 2200:
            print(f"WI unexpected official municipal polygon count {count}; stop without edits")
            return
        candidates=[f for f in meta["fields"] if f["type"]=="esriFieldTypeString" and
                    any(key in f["name"].upper() for key in ("NAME","LABEL","MUNI"))]
        if not candidates:
            print("WI no municipal label column discovered; stop without edits");return
        primary=next((f["name"] for f in candidates if f["name"].upper()=="LABEL"),candidates[0]["name"])
        id_field=meta.get("objectIdField") or "OBJECTID"
        names_by_id={}
        for offset in range(0,count,1500):
            res=client.get(BASE+"/query",params={"f":"json","where":"1=1",
                    "outFields":"*","returnGeometry":"false",
                    "orderByFields":id_field,"resultOffset":offset,"resultRecordCount":1500})
            res.raise_for_status()
            data=res.json()
            if "error" in data: raise ValueError(str(data["error"]))
            for feature in data.get("features",[]):
                x=feature["attributes"]
                k=x.get(id_field)
                if k in names_by_id: raise ValueError(f"Duplicate GIS object {k}")
                names_by_id[k]=x
        if len(names_by_id)!=count:
            print(f"WI fetched {len(names_by_id)}/{count}; no partial import");return
        print("WI sample GIS features",list(names_by_id.values())[:3])
        for ident in ("GEOID","MCD_FIPS","FIPS6","DOA","DOR","DOT","MCD_NAME","LABEL"):
            vals=[str(v.get(ident) or "").strip() for v in names_by_id.values()]
            print(f"WI uniqueness {ident}: {len(set(vals))} distinct over {len(vals)} records, {sum(not v for v in vals)} blank")
        for ident in ("FIPS6","DOA"):
            groups={}
            for attr in names_by_id.values():
                v=str(attr.get(ident) or "").strip()
                groups.setdefault(v,[]).append(attr)
            print(f"WI {ident} blank samples:",[(x.get("CNTY_NAME"),x.get("LABEL"),x.get("MCD_FIPS")) for x in groups.get("",[])[:16]])
            print(f"WI {ident} repeated nonblank key samples:",
                  [(k, [(x.get("CNTY_NAME"),x.get("LABEL")) for x in v[:4]])
                    for k,v in groups.items() if k and len(v)>1][:18])
        def wi_municipal_key(x):
            ctv=str(x.get("CTV") or "").upper().strip()
            name=str(x.get("MCD_NAME") or "").strip().casefold()
            county=str(x.get("CNTY_NAME") or "").strip().casefold()
            return (ctv,county if ctv=="T" else "",name)
        grouped={}
        for item in names_by_id.values():
            grouped.setdefault(wi_municipal_key(item),[]).append(item)
        print("WI grouped true municipalities",len(grouped),
              "by CTV",dict(Counter(key[0] for key in grouped)),
              "merged polygon fragments",sum(len(v)-1 for v in grouped.values()),
              "examples",[(k,len(v)) for k,v in grouped.items() if len(v)>1][:15])
        print("WI selected name field",primary)
        unique={}
        for k,attr in names_by_id.items():
            name=str(attr.get(primary) or "").strip()
            if not name:
                print("WI missing labels: no import");return
            unique.setdefault(name,[]).append(attr)
        print(f"WI raw polygons={count}; unique labels={len(unique)}; duplicate label samples",
              [(n,len(v)) for n,v in unique.items() if len(v)>1][:12])
        if len(unique)>EXPECTED:
            print(f"WI unique municipality labels {len(unique)} > provisional denominator {EXPECTED}; no truncation");return
        additions=0
        for name in sorted(unique):
            key=re.sub(r"[^a-z0-9]+","-",name.lower()).strip("-")
            if append_unique(rows,"WI",name,"municipality",key,
                             f"{BASE}; Wisconsin LTSB July 2026; official clerk directory {DIRECTORY}"):
                additions+=1
        with (root/"us_primary_election_localities.csv").open("w",newline="",encoding="utf-8") as f:
            w=csv.DictWriter(f,fieldnames=FIELDS);w.writeheader();w.writerows(rows)
        print(f"WI imported {additions} unique official GIS municipality labels; remaining provisional gap {EXPECTED-additions}; no local results verified")

if __name__=="__main__":
    main()
