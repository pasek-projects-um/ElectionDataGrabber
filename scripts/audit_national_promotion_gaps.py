from __future__ import annotations

import csv
from collections import Counter, defaultdict
from pathlib import Path
from urllib.parse import urlparse


NEAR_READY_FIELDS = [
    "state",
    "result_url",
    "result_host",
    "access_family",
    "ingest_tier",
    "election_night_candidate",
    "smallest_observed_unit",
    "promotion_blocker",
]

WEB_HOST_FIELDS = [
    "result_host",
    "candidate_count",
    "states",
    "election_night_candidate_count",
    "sample_url",
]


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def classify_promotion_blocker(row: dict[str, str]) -> str:
    url = row.get("result_url", "").lower()
    family = row.get("access_family", "")
    if family == "tabular_download":
        if url.endswith(".xls") or ".xls?" in url:
            return "xls_parser_required"
        if url.endswith(".xlsx") or ".xlsx?" in url:
            return "xlsx_parser_required"
        return "tabular_schema_or_format_review"
    if family == "pdf":
        return "document_adapter"
    if family in {"official_web", "unknown_web"}:
        return "web_platform_signature_unknown"
    return "adapter_completion"


def build_near_ready(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    out = []
    for row in rows:
        if row.get("ingest_tier") != "needs_adapter_completion":
            continue
        enriched = {field: row.get(field, "") for field in NEAR_READY_FIELDS if field != "promotion_blocker"}
        enriched["promotion_blocker"] = classify_promotion_blocker(row)
        out.append(enriched)
    return sorted(out, key=lambda r: (r["promotion_blocker"], r["state"], r["result_url"]))


def build_web_host_summary(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    grouped: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        if row.get("ingest_tier") != "unsupported_web":
            continue
        host = row.get("result_host") or urlparse(row.get("result_url", "")).netloc.lower()
        grouped[host].append(row)

    out = []
    for host, host_rows in grouped.items():
        states = sorted({r.get("state", "") for r in host_rows if r.get("state")})
        night_count = sum(
            1 for r in host_rows if r.get("election_night_candidate", "").lower() == "true"
        )
        out.append(
            {
                "result_host": host,
                "candidate_count": str(len(host_rows)),
                "states": "|".join(states),
                "election_night_candidate_count": str(night_count),
                "sample_url": host_rows[0].get("result_url", ""),
            }
        )
    return sorted(
        out,
        key=lambda r: (
            -int(r["election_night_candidate_count"]),
            -int(r["candidate_count"]),
            r["result_host"],
        ),
    )


def write_rows(path: Path, rows: list[dict[str, str]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    rows = read_rows(root / "audit/national_easy_ingest_candidates.csv")
    write_rows(
        root / "audit/national_promotion_gap_near_ready.csv",
        build_near_ready(rows),
        NEAR_READY_FIELDS,
    )
    write_rows(
        root / "audit/national_web_host_priority.csv",
        build_web_host_summary(rows),
        WEB_HOST_FIELDS,
    )


if __name__ == "__main__":
    main()
