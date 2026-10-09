"""Bounded successor to sweep_national_local_reporting_sources.py."""

import argparse
import csv
import json
from pathlib import Path

from election_data_grabber.national_discovery import Fetcher, run_batch
from scripts.build_national_where_to_look import build


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--registry", type=Path, default=Path("registry"))
    p.add_argument("--seeds", type=Path, help="Optional CSV with url and jurisdiction_id")
    p.add_argument(
        "--checkpoint", type=Path, default=Path("audit/dashboard-discovery/checkpoint.json")
    )
    p.add_argument("--max-publishers", type=int, default=150)
    p.add_argument("--max-requests", type=int, default=300)
    p.add_argument("--max-depth", type=int, default=1)
    p.add_argument("--delay", type=float, default=1.0)
    p.add_argument(
        "--election", default="", help="Explicit election context; never inferred from current year"
    )
    p.add_argument("--retry-failed", action="store_true")
    args = p.parse_args()
    if not (
        1 <= args.max_publishers <= 200
        and 1 <= args.max_requests <= 1000
        and 0 <= args.max_depth <= 3
        and args.delay >= 1
    ):
        p.error("Limits: 1–200 publishers, 1–1000 requests, depth 0–3, delay >=1 second")
    if args.seeds:
        with args.seeds.open(newline="", encoding="utf-8-sig") as f:
            seeds = list(csv.DictReader(f))
    else:
        seeds, _, _ = build(args.registry)
        with (args.registry / "authority_jurisdiction_crosswalk.csv").open(newline="") as f:
            authority = {r["jurisdiction_id"]: r["authority_id"] for r in csv.DictReader(f)}
        for row in seeds:
            row["authority_id"] = authority.get(row["jurisdiction_id"], "")
    fetch = Fetcher(args.delay, max_requests=args.max_requests)
    try:
        result = run_batch(
            seeds,
            args.checkpoint,
            fetch,
            max_publishers=args.max_publishers,
            max_requests=args.max_requests,
            max_depth=args.max_depth,
            election=args.election,
            retry_failed=args.retry_failed,
        )
    finally:
        fetch.close()
    print(json.dumps(result["summary"], indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
