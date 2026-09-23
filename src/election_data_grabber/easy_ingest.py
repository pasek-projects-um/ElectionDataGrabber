from __future__ import annotations

import csv
from collections import defaultdict
from pathlib import Path

from election_data_grabber.state_expansion import classify_result_family

EASY_FAMILIES = {"enhanced_voting", "clarity"}
DOCUMENT_FAMILIES = {"pdf"}
PARTIAL_FAMILIES = {"scytl", "electionware", "tabular_download"}
DISCOVERY_ONLY_FAMILIES = {"civicplus"}
UNSUPPORTED_FAMILIES = {"official_web", "unknown_web"}


def split_result_links(value: str) -> list[str]:
    return [part.strip() for part in value.split(" | ") if part.strip()]


def ingest_tier(family: str, url: str = "") -> str:
    if family in EASY_FAMILIES:
        return "ready_adapter"
    if family == "tabular_download":
        lower = url.lower()
        if lower.endswith(".csv") or ".csv?" in lower:
            return "ready_adapter"
        return "needs_adapter_completion"
    if family in {"scytl", "electionware"}:
        return "needs_adapter_completion"
    if family in DOCUMENT_FAMILIES:
        return "document_adapter"
    if family in DISCOVERY_ONLY_FAMILIES:
        return "discovery_only"
    return "unsupported_web"


def build_candidates(expansion_rows: list[dict[str, str]]) -> list[dict[str, str]]:
    """Explode result links, fingerprint each result URL, and dedupe exact state/result pairs."""
    out, seen = [], set()
    for row in expansion_rows:
        state = row["state"].upper()
        for url in split_result_links(row.get("result_links", "")):
            key = (state, url)
            if key in seen:
                continue
            seen.add(key)
            family = classify_result_family(url)
            out.append(
                {
                    "state": state,
                    "authority_url": row.get("authority_url", ""),
                    "result_url": url,
                    "result_host": url.split("/")[2].lower() if "://" in url else "",
                    "access_family": family,
                    "ingest_tier": ingest_tier(family, url),
                    "election_night_candidate": row.get("election_night_candidate", ""),
                    "smallest_observed_unit": row.get("smallest_observed_unit", "unknown") or "unknown",
                }
            )
    return sorted(
        out,
        key=lambda r: (
            r["ingest_tier"],
            r["access_family"],
            r["state"],
            r["result_url"],
        ),
    )


def summarize(candidates: list[dict[str, str]], denominators: dict[str, int]) -> list[dict[str, str]]:
    groups = defaultdict(list)
    for row in candidates:
        groups[(row["ingest_tier"], row["access_family"])].append(row)

    out = []
    for (tier, family), rows in groups.items():
        states = sorted({r["state"] for r in rows})
        out.append(
            {
                "ingest_tier": tier,
                "access_family": family,
                "unique_result_urls": str(len(rows)),
                "states": "|".join(states),
                "state_count": str(len(states)),
                "expected_units_exposed": str(sum(denominators.get(s, 0) for s in states)),
            }
        )

    return sorted(
        out,
        key=lambda r: (
            {
                "ready_adapter": 0,
                "needs_adapter_completion": 1,
                "document_adapter": 2,
                "discovery_only": 3,
                "unsupported_web": 4,
            }.get(r["ingest_tier"], 9),
            -int(r["expected_units_exposed"]),
            r["access_family"],
        ),
    )


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))
