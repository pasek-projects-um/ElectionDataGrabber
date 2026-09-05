"""Build a national county/county-equivalent registry from the U.S. Census Gazetteer.

Source: 2025 National Counties Gazetteer (50 states, DC, Puerto Rico).
The output is a stable jurisdiction backbone; election-result source URLs are attached later.
"""

from __future__ import annotations

import csv
import io
import zipfile
from pathlib import Path

import httpx


URL = "https://www2.census.gov/geo/docs/maps-data/data/gazetteer/2025_Gazetteer/2025_Gaz_counties_national.zip"
OUT = Path("registry/us_counties_2025.csv")


def main() -> None:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    response = httpx.get(URL, timeout=120, follow_redirects=True)
    response.raise_for_status()

    with zipfile.ZipFile(io.BytesIO(response.content)) as zf:
        name = next(n for n in zf.namelist() if n.lower().endswith(".txt"))
        text = zf.read(name).decode("utf-8-sig")

    rows = list(csv.DictReader(io.StringIO(text), delimiter="\t"))
    fields = [
        "USPS",
        "GEOID",
        "ANSICODE",
        "NAME",
        "ALAND",
        "AWATER",
        "ALAND_SQMI",
        "AWATER_SQMI",
        "INTPTLAT",
        "INTPTLONG",
    ]

    with OUT.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({k: (row.get(k) or "").strip() for k in fields})

    print(f"Wrote {len(rows)} county/county-equivalent records to {OUT}")


if __name__ == "__main__":
    main()
