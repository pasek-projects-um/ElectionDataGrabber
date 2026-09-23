from __future__ import annotations

import argparse
import csv
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

from election_data_grabber.execution_maturity import maturity_row
from election_data_grabber.supported_execution import execute_supported_body

FIELDS = [
    "state",
    "result_url",
    "access_family",
    "parser",
    "execution_stage",
    "observation_count",
    "smallest_observed_unit",
    "vote_modes_preserved",
    "failure_class",
    "snapshot_sha256",
]


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def fetch_body(url: str, timeout: int) -> tuple[bytes | None, str]:
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "ElectionDataGrabber/1.0 national-execution-audit"},
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.read(), ""
    except urllib.error.HTTPError as exc:
        return None, f"http_{exc.code}"
    except urllib.error.URLError:
        return None, "network_error"
    except TimeoutError:
        return None, "timeout"


def failed_row(row: dict[str, str], failure_class: str) -> dict[str, str]:
    return {
        "state": row.get("state", ""),
        "result_url": row.get("result_url", ""),
        "access_family": row.get("access_family", ""),
        "parser": row.get("parser", ""),
        "execution_stage": "discovered",
        "observation_count": "0",
        "smallest_observed_unit": row.get("smallest_observed_unit", "unknown"),
        "vote_modes_preserved": "",
        "failure_class": failure_class,
        "snapshot_sha256": "",
    }


def run(
    manifest_path: Path,
    output_path: Path,
    *,
    timeout: int = 15,
    limit: int | None = None,
) -> list[dict[str, str]]:
    rows = read_rows(manifest_path)
    if limit is not None:
        rows = rows[:limit]

    out: list[dict[str, str]] = []
    fetched_at = datetime.now(timezone.utc)
    for index, row in enumerate(rows, start=1):
        url = row["result_url"]
        body, failure = fetch_body(url, timeout)
        if body is None:
            out.append(failed_row(row, failure))
            continue

        evidence = execute_supported_body(
            row,
            body,
            election_id="national-execution-audit",
            jurisdiction_id=f"us:{row['state'].lower()}:source-{index}",
            source_id=f"national-execution:{index}",
            fetched_at=fetched_at,
        )
        out.append(maturity_row(evidence))

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(out)
    return out


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--manifest",
        type=Path,
        default=Path("audit/national_supported_ingest_manifest.csv"),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("audit/national_supported_execution.csv"),
    )
    parser.add_argument("--timeout", type=int, default=15)
    parser.add_argument("--limit", type=int)
    args = parser.parse_args()
    run(args.manifest, args.output, timeout=args.timeout, limit=args.limit)


if __name__ == "__main__":
    main()
