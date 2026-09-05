from __future__ import annotations

import csv
from collections import Counter
from pathlib import Path


def score(path: Path = Path("registry/oh_county_capabilities.csv")) -> dict[str, int | float]:
    with path.open(encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))
    counts = Counter(row["portability_class"] for row in rows)
    n = len(rows)
    reusable = counts.get("A", 0) + counts.get("B", 0)
    generalized = reusable + counts.get("C", 0)
    return {
        "counties": n,
        "A": counts.get("A", 0),
        "B": counts.get("B", 0),
        "C": counts.get("C", 0),
        "D": counts.get("D", 0),
        "E": counts.get("E", 0),
        "A_or_B_share": reusable / n if n else 0.0,
        "A_B_or_C_share": generalized / n if n else 0.0,
    }


if __name__ == "__main__":
    result = score()
    for key, value in result.items():
        print(f"{key}={value}")
