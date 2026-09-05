"""Michigan county election-platform census.

Enumerates Michigan counties from the Census registry when available, falling
back to the authority registry so the statewide census remains runnable in a
fresh checkout. Official authority URLs are kept in CSV so discoveries can be
reviewed and rerun without code changes.
"""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

from election_data_grabber.discovery import discover_result_links

FIELDS = [
    "county_geoid",
    "county",
    "authority_url",
    "result_url",
    "label",
    "platform",
    "status",
    "error",
]


def load_authorities(path: Path) -> dict[str, str]:
    with path.open(encoding="utf-8-sig") as f:
        return {
            row["county"].strip(): row["authority_url"].strip()
            for row in csv.DictReader(f)
            if row.get("county") and row.get("authority_url")
        }


def load_counties(counties_path: Path, authorities: dict[str, str]) -> list[dict[str, str]]:
    if counties_path.exists():
        with counties_path.open(encoding="utf-8-sig") as f:
            rows = [row for row in csv.DictReader(f) if row.get("USPS") == "MI"]
        return [
            {
                "county": row["NAME"].removesuffix(" County"),
                "county_geoid": row.get("GEOID", ""),
            }
            for row in rows
        ]
    return [
        {"county": county, "county_geoid": ""}
        for county in sorted(authorities)
    ]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--counties", type=Path, default=Path("registry/us_counties_2025.csv"))
    ap.add_argument("--authorities", type=Path, default=Path("registry/mi_county_authorities.csv"))
    ap.add_argument("--out", type=Path, default=Path("registry/mi_county_platform_census.csv"))
    ap.add_argument("--limit", type=int, default=None, help="Optional county limit for smoke tests")
    args = ap.parse_args()

    authorities = load_authorities(args.authorities)
    counties = load_counties(args.counties, authorities)
    if len(authorities) != 83:
        raise SystemExit(f"Expected 83 Michigan county authorities, found {len(authorities)}")
    if len(counties) != 83:
        raise SystemExit(f"Expected 83 Michigan counties, found {len(counties)}")
    if args.limit is not None:
        counties = counties[: args.limit]

    rows = []
    for item in counties:
        county = item["county"]
        authority = authorities.get(county, "")
        if not authority:
            rows.append(
                dict(
                    county_geoid=item["county_geoid"],
                    county=county,
                    authority_url="",
                    result_url="",
                    label="",
                    platform="",
                    status="authority_missing",
                    error="",
                )
            )
            continue
        try:
            links = discover_result_links(authority)
            if not links:
                rows.append(
                    dict(
                        county_geoid=item["county_geoid"],
                        county=county,
                        authority_url=authority,
                        result_url="",
                        label="",
                        platform="",
                        status="no_result_link_found",
                        error="",
                    )
                )
            for source in links:
                rows.append(
                    dict(
                        county_geoid=item["county_geoid"],
                        county=county,
                        authority_url=authority,
                        result_url=source.url,
                        label=source.label,
                        platform=source.platform or "unknown",
                        status="candidate",
                        error="",
                    )
                )
        except Exception as exc:
            rows.append(
                dict(
                    county_geoid=item["county_geoid"],
                    county=county,
                    authority_url=authority,
                    result_url="",
                    label="",
                    platform="",
                    status="fetch_error",
                    error=type(exc).__name__,
                )
            )

    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    print(json.dumps({"counties": len(counties), "rows": len(rows), "output": str(args.out)}))


if __name__ == "__main__":
    main()
