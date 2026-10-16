"""One bounded monitoring pass; schedule repeatedly on a persistent worker."""

import argparse
import csv
import fcntl
import json
import time
from contextlib import contextmanager
from pathlib import Path

from election_data_grabber.authority_directory import FIELDS
from election_data_grabber.discovery_watch import WatchFetcher, follow_candidates, run_watch
from election_data_grabber.national_discovery import save
from election_data_grabber.source_context import CONTEXT_FIELDS, source_context


@contextmanager
def worker_lock(path):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a") as stream:
        try:
            fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise RuntimeError("A watcher already owns this state directory") from None
        try:
            yield
        finally:
            fcntl.flock(stream, fcntl.LOCK_UN)


def export_queue(path, state):
    rows = []
    for url, candidate in sorted(state["candidates"].items()):
        rows.append({
            **source_context(url),
            "url": url, "score": candidate["score"],
            "signatures": " | ".join(candidate["signatures"]),
            "parent_pages": " | ".join(candidate["parent_pages"]),
            "first_observed_at": candidate["first_observed_at"],
            "last_observed_at": candidate["last_observed_at"],
            "source_snapshot_sha256": candidate["source_snapshot_sha256"],
            "next_action": candidate["next_action"],
            "served_jurisdiction_verified": "false", "live_coverage": "false",
        })
    fields = ["url", "score", "signatures", "parent_pages", "first_observed_at",
              "last_observed_at", "source_snapshot_sha256", "next_action",
              "served_jurisdiction_verified", "live_coverage", *CONTEXT_FIELDS]
    temp = path.with_suffix(".tmp")
    with temp.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    temp.replace(path)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seeds", type=Path,
                        default=Path("audit/national-layers/unique-start-pages.csv"))
    parser.add_argument("--state-dir", type=Path, default=Path("watch-data"))
    parser.add_argument("--registry", type=Path, default=Path("registry"),
                        help="Named-unit registry for directory link extraction")
    parser.add_argument("--source-seeds", type=Path,
                        default=Path("audit/national-layers/source-next-actions.csv"))
    parser.add_argument("--directory-seeds", type=Path,
                        help="Unverified directory inspection leads with retained provenance")
    parser.add_argument("--local-site-leads", type=Path,
                        default=Path("registry/local_site_discovery_leads.csv"),
                        help="Fresh observed search leads; validated against named units")
    parser.add_argument("--max-depth", type=int, default=2,
                        help="Follow observed HTML candidates on later passes, depth 0–3")
    parser.add_argument("--interval", type=int, default=3600,
                        help="Seconds before revisiting a successful page (minimum 60)")
    parser.add_argument("--max-pages", type=int, default=100)
    parser.add_argument("--max-requests", type=int, default=300)
    parser.add_argument("--max-bytes", type=int, default=1_000_000)
    parser.add_argument("--delay", type=float, default=1.0)
    parser.add_argument("--states", nargs="*", default=[])
    parser.add_argument("--dry-run", action="store_true",
                        help="Show validated seed inventory; no network or state writes")
    args = parser.parse_args()
    if not (60 <= args.interval <= 86400 and 1 <= args.max_pages <= 1000
            and 1 <= args.max_requests <= 3000 and args.delay >= 1
            and 1024 <= args.max_bytes <= 10_000_000 and 0 <= args.max_depth <= 3):
        parser.error("Invalid interval, page/request/byte budget, or host delay")
    with args.seeds.open(newline="", encoding="utf-8-sig") as stream:
        seeds = list(csv.DictReader(stream))
    if args.source_seeds.exists():
        with args.source_seeds.open(newline="", encoding="utf-8-sig") as stream:
            seeds.extend(row for row in csv.DictReader(stream)
                         if row.get("catalog_kind") != "result_artifact_lead")
    if args.directory_seeds:
        with args.directory_seeds.open(newline="", encoding="utf-8-sig") as stream:
            seeds.extend(csv.DictReader(stream))
    locality_path = args.registry / "us_primary_election_localities.csv"
    with locality_path.open(newline="", encoding="utf-8-sig") as stream:
        localities = list(csv.DictReader(stream))
    if args.local_site_leads.exists():
        from election_data_grabber.local_site_discovery import inspection_seeds

        with args.local_site_leads.open(newline="", encoding="utf-8-sig") as stream:
            fresh, rejected = inspection_seeds(csv.DictReader(stream), localities)
        if rejected:
            raise ValueError(f"{rejected} invalid local-site discovery rows; inspect lead ledger")
        seeds.extend(fresh)
    if args.states:
        wanted = {s.upper() for s in args.states}
        seeds = [s for s in seeds if wanted.intersection(
            value.strip() for value in s.get("states", s.get("state", "")).split("|"))]
    if args.dry_run:
        from election_data_grabber.discovery_watch import seed_groups

        print(json.dumps({"seed_pages": len(seed_groups(seeds)), "http_requests": 0,
                          "state_writes": 0, "interval_seconds": args.interval,
                          "max_pages": args.max_pages, "max_requests": args.max_requests},
                         sort_keys=True))
        return
    with worker_lock(args.state_dir / "worker.lock"):
        state_path = args.state_dir / "state.json"
        previous = json.loads(state_path.read_text()) if state_path.exists() else {}
        seeds = follow_candidates(seeds, previous, args.max_depth)
        if args.states:
            seeds = [s for s in seeds if wanted.intersection(
                value.strip() for value in s.get("states", s.get("state", "")).split("|"))]
        fetch = WatchFetcher(args.delay, max_bytes=args.max_bytes, max_requests=args.max_requests)
        try:
            state, _, summary = run_watch(
                seeds, args.state_dir / "state.json", args.state_dir / "snapshots", fetch,
                now=time.time(), interval=args.interval, max_pages=args.max_pages,
                localities=localities,
            )
        finally:
            fetch.close()
        export_queue(args.state_dir / "candidate-queue.csv", state)
        authority_path = args.state_dir / "authority-link-queue.csv"
        authority_rows = list(state.get("authority_candidates", {}).values())
        temp = authority_path.with_suffix(".tmp")
        with temp.open("w", newline="", encoding="utf-8") as stream:
            # Use a stable header even on the initial pass with no directory rows.
            fields = [*FIELDS, "first_observed_at", "last_observed_at"]
            writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\n")
            writer.writeheader()
            writer.writerows(authority_rows)
        temp.replace(authority_path)
        save(args.state_dir / "last-run.json", summary)
        print(json.dumps(summary, sort_keys=True))


if __name__ == "__main__":
    main()
