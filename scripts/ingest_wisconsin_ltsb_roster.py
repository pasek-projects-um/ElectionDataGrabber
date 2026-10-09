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
        # One town-name per county; cities and villages spanning county lines
        # are one municipality.  Preserve county authorities as a separate
        # level rather than embedding them in a fictitious 1850-unit total.
        counties=sorted({str(x.get("CNTY_NAME") or "").strip() for x in names_by_id.values()})
        if len(grouped)!=1849 or len(counties)!=72 or any(not x for x in counties):
            raise ValueError(f"WI official roster unexpectedly {len(grouped)} municipalities/{len(counties)} counties")
        expected_all=len(grouped)+len(counties)
        # This script owns only the newly generated, still-unresolved WI
        # candidates; do not delete independently verified/source-linked rows.
        prior=[x for x in rows if x["state"]=="WI"]
        if any(x.get("coverage_status")!="enumerated_unresolved" or x.get("final_source_id") or
               x.get("election_night_source_id") for x in prior):
            raise ValueError("WI existing linked/verified rows require manual crosswalk before replacement")
        rows=[x for x in rows if x["state"]!="WI"]
        for (typ,county,name),items in sorted(grouped.items()):
            level={"C":"city","T":"town","V":"village"}[typ]
            label=str(items[0].get("MCD_NAME") or "").strip().title()
            parent=county.title() if county else ""
            full=f"{level.title()} of {label}" + (f" ({parent} County)" if typ=="T" else "")
            suffix=re.sub(r"[^a-z0-9]+","-",f"{typ}-{county}-{name}").strip("-")
            item=dict.fromkeys(FIELDS,"")
            item.update(jurisdiction_id=f"us:wi:ltsb2026:{suffix}",state="WI",
                jurisdiction_level=level,canonical_name=full,
                external_id_namespace="wi_ltsb_ctv_july_2026",
                external_id="|".join(sorted(str(i.get("GEOID")) for i in items)),
                id_status="state_official_2026_gis",coverage_status="enumerated_unresolved",
                final_capable="false",election_night_capable="false",
                assessment_method="2026_wi_ltsb_municipal_boundary_gis",
                assessment_status="enumerated_not_source_verified",
                notes=f"WI LTSB July 2026 city/town/village boundary; source={BASE}; county fragments={len(items)}; local election results not verified; clerk directory={DIRECTORY}")
            rows.append(item)
        for county in counties:
            suffix=re.sub(r"[^a-z0-9]+","-",county.lower()).strip("-")
            item=dict.fromkeys(FIELDS,"")
            item.update(jurisdiction_id=f"us:wi:ltsb2026:county-{suffix}",state="WI",
                jurisdiction_level="county",canonical_name=f"{county.title()} County",
                external_id_namespace="wi_ltsb_2026_county_name",
                external_id=county,id_status="state_official_2026_gis",
                coverage_status="enumerated_unresolved",final_capable="false",
                election_night_capable="false",
                assessment_method="2026_wi_ltsb_municipal_boundary_gis_counties",
                assessment_status="enumerated_not_source_verified",
                notes=f"WI county-level election administration layer, deduplicated county name from LTSB municipal GIS: {BASE}; direct result URL not verified.")
            rows.append(item)
        with (root/"us_primary_election_localities.csv").open("w",newline="",encoding="utf-8") as f:
            w=csv.DictWriter(f,fieldnames=FIELDS);w.writeheader();w.writerows(rows)
        denominator=root/"us_primary_election_locality_denominators.csv"
        with denominator.open(newline="",encoding="utf-8-sig") as f:
            dr=csv.DictReader(f);columns=dr.fieldnames;all_den=list(dr)
        wi=[x for x in all_den if x["state"]=="WI"]
        if len(wi)!=1 or int(wi[0]["expected_primary_units"]) not in (1850,expected_all):
            raise ValueError("WI historical denominator changed unexpectedly")
        wi[0].update(expected_primary_units=str(expected_all),
            evidence_url=BASE,evidence_method="2026_wi_ltsb_1849_municipalities_plus_72_counties",
            notes="Provisional authority model: 1849 unique cities/towns/villages + 72 county clerks; deduplicate overlapping geography; these are named candidates not verified local result endpoints.")
        with denominator.open("w",newline="",encoding="utf-8") as f:
            w=csv.DictWriter(f,fieldnames=columns);w.writeheader();w.writerows(all_den)
        print(f"WI imported {len(grouped)} municipality plus {len(counties)} county named candidates; {expected_all} WI records; 0 unnamed against revised, source-backed provisional WI denominator")

if __name__=="__main__":
    main()
