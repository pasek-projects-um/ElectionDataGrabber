from __future__ import annotations

import argparse
import csv
import urllib.error
import urllib.request
from pathlib import Path

from election_data_grabber.platform_fingerprint import fingerprint_result_surface

FIELDS = [
    "result_host",
    "sample_url",
    "candidate_count",
    "election_night_candidate_count",
    "family",
    "confidence",
    "evidence",
    "discovered_artifacts",
    "fetch_failure",
]


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def fetch_text(url: str, timeout: int) -> tuple[str | None, str]:
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "ElectionDataGrabber/1.0 platform-probe"},
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read()
            return body.decode("utf-8", errors="replace"), ""
    except urllib.error.HTTPError as exc:
        return None, f"http_{exc.code}"
    except urllib.error.URLError:
        return None, "network_error"
    except TimeoutError:
        return None, "timeout"


def probe(rows: list[dict[str, str]], *, timeout: int = 10, limit: int | None = None) -> list[dict[str, str]]:
    ranked = sorted(
        rows,
        key=lambda r: (
            -int(r.get("election_night_candidate_count", "0") or 0),
            -int(r.get("candidate_count", "0") or 0),
            r.get("result_host", ""),
        ),
    )
    if limit is not None:
        ranked = ranked[:limit]

    out = []
    for row in ranked:
        url = row.get("sample_url", "")
        text, failure = fetch_text(url, timeout)
        if text is None:
            out.append({
                "result_host": row.get("result_host", ""),
                "sample_url": url,
                "candidate_count": row.get("candidate_count", "0"),
                "election_night_candidate_count": row.get("election_night_candidate_count", "0"),
                "family": "",
                "confidence": "",
                "evidence": "",
                "discovered_artifacts": "",
                "fetch_failure": failure,
            })
            continue

        fp = fingerprint_result_surface(url, text)
        out.append({
            "result_host": row.get("result_host", ""),
            "sample_url": url,
            "candidate_count": row.get("candidate_count", "0"),
            "election_night_candidate_count": row.get("election_night_candidate_count", "0"),
            "family": fp.family,
            "confidence": fp.confidence,
            "evidence": "|".join(fp.evidence),
            "discovered_artifacts": "|".join(fp.discovered_artifacts),
            "fetch_failure": "",
        })
    return out


def write_rows(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--input",
        type=Path,
        default=Path("audit/national_web_host_priority.csv"),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("audit/national_platform_probe.csv"),
    )
    parser.add_argument("--timeout", type=int, default=10)
    parser.add_argument("--limit", type=int, default=25)
    args = parser.parse_args()

    rows = probe(read_rows(args.input), timeout=args.timeout, limit=args.limit)
    write_rows(args.output, rows)


if __name__ == "__main__":
    main()
