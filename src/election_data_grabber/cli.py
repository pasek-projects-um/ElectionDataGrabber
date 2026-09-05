from __future__ import annotations

import json
from dataclasses import asdict

import typer

from election_data_grabber.discovery import discover_result_links

app = typer.Typer(no_args_is_help=True)


@app.command()
def discover(url: str) -> None:
    """Find likely election-results links on an election authority page."""
    links = discover_result_links(url)
    typer.echo(json.dumps([asdict(x) for x in links], indent=2))


if __name__ == "__main__":
    app()
