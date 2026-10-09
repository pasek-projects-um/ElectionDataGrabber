"""Bounded import of remaining tractable national jurisdiction names.

All external feeds are official Census/state GIS sources. Names are *not*
proof that an election-results endpoint exists. Do not count candidate
county geographies as verified independent local election authorities.
"""
from __future__ import annotations
import csv
import re
from collections import Counter
from pathlib import Path
import httpx
from expand_census_county_starts import CENSUS_URL, FIELDS, expand

RI_URL = "https://risegis.ri.gov/hosting/rest/services/Statewide/TownsCounties/MapServer/2/query"
NH_URL = "https://maps.dot.nh.gov/arcgis_server/rest/services/ProjectViewer/NHDOT_PROJECT_VIEWER_DOT_BASEMAP/MapServer/39/query"
RI_DIRECTORY = "https://elections.ri.gov/about-us/local-boards-canvassers"
NH_DIRECTORY = "https://www.sos.nh.gov/elections"
DC_DIRECTORY = "https://dcboe.org/"
AK_DIRECTORY = "https://www.elections.alaska.gov/"

def records(root: Path):
    with (root / "us_primary_election_localities.csv").open(newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))

def unique_name(row):
    return row["state"], re.sub(r"\s+", " ", row["canonical_name"].strip()).casefold()

def append_unique(rows, state, name, level, key, provenance, external_id="", namespace=""):
    if (state, name.casefold()) in {unique_name(r) for r in rows}:
        return False
    item = dict.fromkeys(FIELDS, "")
    item.update(jurisdiction_id=f"us:{state.lower()}:priority-roster:{key}",
                state=state, jurisdiction_level=level, canonical_name=name,
                external_id_namespace=namespace, external_id=str(external_id),
                id_status="source_roster_name", coverage_status="enumerated_unresolved",
                final_capable="false", election_night_capable="false",
                assessment_method="official_state_directory_or_gis",
                assessment_status="enumerated_not_source_verified",
                notes=f"Official named roster / starting directory: {provenance}; results endpoint and ownership not yet verified.")
    rows.append(item)
    return True

def arcgis_names(client, url, fields, field="NAME"):
    response = client.get(url, params={"where": "1=1", "outFields": ",".join(fields),
                                       "returnGeometry": "false", "f": "json"}, timeout=90)
    response.raise_for_status()
    payload = response.json()
    if "error" in payload or "features" not in payload:
        raise ValueError(f"Invalid GIS roster {url}: {payload.get('error', payload)}")
    return [x["attributes"] for x in payload["features"]]

def main():
    root = Path("registry")
    client = httpx.Client(timeout=120, follow_redirects=True)
    census_response = client.get(CENSUS_URL)
    census_response.raise_for_status()
    rows, from_counties = expand(root, census_response.content)
    added = Counter(row["state"] for row in from_counties)
    # Explicit single election authorities, not fictitious county subdivisions.
    for st, title, url in (("AK", "Alaska Division of Elections", AK_DIRECTORY),
                           ("DC", "District of Columbia Board of Elections", DC_DIRECTORY)):
        if append_unique(rows, st, title, "state_election_authority" if st == "AK" else "district",
                         "central", url):
            added[st] += 1
    ri = arcgis_names(client, RI_URL, ["NAME"])
    ri_names = sorted({str(x["NAME"]).strip() for x in ri if x.get("NAME")})
    if len(ri_names) != 39:
        raise ValueError(f"RI source unexpectedly lists {len(ri_names)} municipalities, expected 39")
    for name in ri_names:
        if append_unique(rows, "RI", name, "municipality", re.sub(r"[^a-z0-9]+", "-", name.lower()),
                         f"{RI_URL}; election directory {RI_DIRECTORY}"):
            added["RI"] += 1
    # NH GIS includes unincorporated areas; only promote an explicit city/town
    # subset when its unique names reconcile exactly with 234 municipalities.
    nh = arcgis_names(client, NH_URL, ["NAME", "CITYTOWN", "NON_ATT_AREA"])
    eligible = [x for x in nh if str(x.get("CITYTOWN", "")).strip().lower() in
                ("city", "town", "cities", "towns")]
    nh_names = sorted({str(x["NAME"]).strip() for x in eligible if x.get("NAME")})
    if len(nh_names) != 234:
        print(f"NH official GIS city/town filter returned {len(nh_names)} rather than 234; no speculative NH names imported")
    else:
        for name in nh_names:
            if append_unique(rows, "NH", name, "municipality", re.sub(r"[^a-z0-9]+", "-", name.lower()),
                             f"{NH_URL}; {NH_DIRECTORY}"):
                added["NH"] += 1
    # Never overwrite an existing record; retain source classification as unverified.
    with (root / "us_primary_election_localities.csv").open("w", encoding="utf-8", newline="") as out:
        writer = csv.DictWriter(out, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    print(f"Priority roster additions: {dict(sorted(added.items()))}; total {sum(added.values())}")
    print("IL municipal commissions and MO split authorities remain unresolved until authoritative crosswalks are validated.")

if __name__ == "__main__":
    main()
