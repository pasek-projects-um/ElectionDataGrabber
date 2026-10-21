from __future__ import annotations

import json
from dataclasses import asdict

import typer

from election_data_grabber.discovery import discover_result_links

app = typer.Typer(no_args_is_help=True, pretty_exceptions_show_locals=False)


@app.command()
def discover(url: str) -> None:
    """Find likely election-results links on an election authority page."""
    links = discover_result_links(url)
    typer.echo(json.dumps([asdict(x) for x in links], indent=2))


@app.command()
def collect(
    manifest: str,
    state_dir: str = "election-night-data",
    time_budget: int = 120,
    max_feeds: int = 25,
) -> None:
    """Run one resumable bounded pass over explicitly selected result feeds."""
    import signal
    import time
    from pathlib import Path

    from election_data_grabber.election_night import FeedFetcher, collect, load_manifest

    config = load_manifest(Path(manifest))
    fetch = FeedFetcher(delay=1, max_bytes=10_000_000, max_requests=200)
    fetch.deadline = time.monotonic() + time_budget

    def stop(signum, frame):
        fetch.stopping = True

    handlers = {sig: signal.signal(sig, stop) for sig in (signal.SIGINT, signal.SIGTERM)}
    try:
        summary = collect(
            config, Path(state_dir), fetch=fetch, time_budget=time_budget, max_feeds=max_feeds
        )
    finally:
        fetch.close()
        for sig, handler in handlers.items():
            signal.signal(sig, handler)
    typer.echo(json.dumps(summary, indent=2, sort_keys=True))
    if (
        not summary["enabled_feeds"]
        or summary["stale_enabled_feeds"]
        or any(row["status"] in ("failed", "review_required") for row in summary["results"])
    ):
        raise typer.Exit(1)


@app.command()
def status(manifest: str, state_dir: str = "election-night-data") -> None:
    """Report freshness and replay readiness for selected feeds only."""
    from pathlib import Path

    from election_data_grabber.election_night import load_manifest, report

    summary = report(load_manifest(Path(manifest)), Path(state_dir))
    typer.echo(json.dumps(summary, indent=2, sort_keys=True))
    if (
        not summary["enabled_feeds"]
        or summary["stale_enabled_feeds"]
        or any(row["enabled"] and row["status"] != "ok" for row in summary["feeds"])
    ):
        raise typer.Exit(1)


@app.command()
def replay(state_dir: str, sample: str) -> None:
    """Verify a captured sample by parsing its preserved bytes without network."""
    from pathlib import Path

    from election_data_grabber.election_night import replay_sample

    typer.echo(json.dumps(replay_sample(Path(state_dir), sample), indent=2, sort_keys=True))


@app.command()
def readiness(
    manifest: str = "config/election-night-2026.json",
    registry: str = "registry",
    state_dir: str = "election-night-data",
    output: str = "audit/election-night-readiness",
):
    """Write national coverage and selected-feed operational readiness separately."""
    import csv
    from pathlib import Path

    from election_data_grabber.election_night import load_manifest
    from election_data_grabber.election_readiness import readiness

    evidence = readiness(Path(registry), load_manifest(Path(manifest)), Path(state_dir))
    target = Path(output)
    target.mkdir(parents=True, exist_ok=True)
    (target / "readiness.json").write_text(json.dumps(evidence, indent=2, sort_keys=True) + "\n")
    if evidence["states"]:
        with (target / "by-state.csv").open("w", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=list(evidence["states"][0]))
            writer.writeheader()
            writer.writerows(evidence["states"])
    typer.echo(
        json.dumps(
            {key: value for key, value in evidence.items() if key != "states"},
            indent=2,
            sort_keys=True,
        )
    )


@app.command("verify-refresh")
def verify_refresh(
    manifest: str,
    old_sample: str,
    new_sample: str,
    evidence_url: str = typer.Option(...),
    note: str = typer.Option(...),
    state_dir: str = "election-night-data",
):
    """Record an operator review of two accepted, changing election captures."""
    from pathlib import Path

    from election_data_grabber.election_night import load_manifest
    from election_data_grabber.election_refresh import verify_refresh

    result = verify_refresh(
        load_manifest(manifest),
        Path(state_dir),
        old_sample,
        new_sample,
        evidence_url=evidence_url,
        note=note,
    )
    typer.echo(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    app()
