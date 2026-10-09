"""Expand county-administered primary election units using the 2025 Census Gazetteer.

Only states whose primary election denominator is county/county-equivalent based
are eligible. Census geographic names are evidence for enumeration, not election
authority verification. Existing records are never overwritten.
"""
from __future__ import annotations

import csv
import io
import re
import zipfile
from collections import Counter
from pathlib import Path

import httpx

CENSUS_URL = "https://www2.census.gov/geo/docs/maps-data/data/gazetteer/2025_Gazetteer/2025_Gaz_counties_national.zip"
COUNTY_MODELS = {"county", "county+state", "county+independent-city",
                 "county+board-of-elections", "county+municipal/election-district",
                 "parish", "county+state/local"}
FIELDS = ("jurisdiction_id", "state", "jurisdiction_level", "canonical_name",
          "external_id_namespace", "external_id", "id_status", "authority_id",
          "coverage_status", "final_capable", "election_night_capable",
          "final_evidence_url", "election_night_evidence_url", "final_source_id",
          "election_night_source_id", "assessment_method", "assessment_status",
          "first_verified_at", "last_verified_at", "notes")


def expand(root: Path, gazetteer_bytes: bytes):
    with (root / "us_primary_election_locality_denominators.csv").open(newline="", encoding="utf-8-sig") as f:
        denominator = {row["state"]: row for row in csv.DictReader(f)}
    with (root / "us_primary_election_localities.csv").open(newline="", encoding="utf-8-sig") as f:
        current = list(csv.DictReader(f))
    def normalized(name):
        return re.sub(r"\\s+(county|parish|borough|census area)$", "", name.strip(), flags=re.I).casefold()

    existing = {(row["state"], normalized(row["canonical_name"])) for row in current}
    with zipfile.ZipFile(io.BytesIO(gazetteer_bytes)) as zf:
        txt = next(name for name in zf.namelist() if name.lower().endswith(".txt"))
        gazetteer_text = zf.read(txt).decode("utf-8-sig")
        first_line = gazetteer_text.splitlines()[0]
        delimiter = "|" if "|" in first_line else "\t"
        source = list(csv.DictReader(io.StringIO(gazetteer_text), delimiter=delimiter, skipinitialspace=True))
    added = []
    per_state = Counter(row["state"] for row in current)
    for row in source:
        row = {key.strip(): (value or "").strip() for key, value in row.items() if key is not None}
        state = row.get("USPS") or row.get("USPS Code") or row.get("STATE") or row.get("STATE_ABBR") or ""
        if not state:
            raise ValueError(f"Unexpected Census Gazetteer columns: {sorted(row)}")
        d = denominator.get(state)
        if not d or d["authority_model"].strip() not in COUNTY_MODELS:
            continue
        geoid = row["GEOID"].strip()
        name = row["NAME"].strip()
        if not re.fullmatch(r"\d{5}", geoid) or not name:
            continue
        if (state, normalized(name)) in existing:
            continue
        if per_state[state] >= int(d["expected_primary_units"]):
            continue
        level = "parish" if state == "LA" else "county_equivalent"
        item = dict.fromkeys(FIELDS, "")
        item.update(jurisdiction_id=f"us:{state.lower()}:census-county:{geoid}",
                    state=state, jurisdiction_level=level, canonical_name=name,
                    external_id_namespace="census_geoid_2025", external_id=geoid,
                    id_status="census_geoid", coverage_status="enumerated_unresolved",
                    final_capable="false", election_night_capable="false",
                    assessment_method="2025_census_county_gazetteer",
                    assessment_status="enumerated_not_source_verified",
                    notes=f"2025 Census Gazetteer county-equivalent; official election authority not yet verified. {CENSUS_URL}")
        current.append(item)
        added.append(item)
        existing.add((state, normalized(name)))
        per_state[state] += 1
    return current, added


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--registry", default="registry")
    parser.add_argument("--min-additions", type=int, default=1000)
    args = parser.parse_args()
    root = Path(args.registry)
    response = httpx.get(CENSUS_URL, timeout=120, follow_redirects=True)
    response.raise_for_status()
    rows, added = expand(root, response.content)
    if len(added) < args.min_additions:
        raise SystemExit(f"Only {len(added)} new units; expected >= {args.min_additions}. No file changed.")
    path = root / "us_primary_election_localities.csv"
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    print(f"Added {len(added)} Census-backed named units, no election URLs inferred")


if __name__ == "__main__":
    main()
