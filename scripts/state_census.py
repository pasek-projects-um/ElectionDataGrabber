from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

import httpx

STATE_REPOS = {
    "MI": "openelections/openelections-data-mi",
    "OH": "openelections/openelections-data-oh",
}


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument("--state", required=True, choices=sorted(STATE_REPOS))
    p.add_argument("--output", required=True)
    return p.parse_args()


def github_contents(client: httpx.Client, repo: str, path: str) -> list[dict]:
    url = f"https://api.github.com/repos/{repo}/contents/{path}"
    r = client.get(url)
    r.raise_for_status()
    data = r.json()
    return data if isinstance(data, list) else [data]


def inspect_csv(client: httpx.Client, item: dict) -> dict:
    r = client.get(item["download_url"])
    r.raise_for_status()
    rows = list(csv.DictReader(r.text.splitlines()))
    columns = list(rows[0].keys()) if rows else []
    precinct_col = next((c for c in columns if c.lower() in {"precinct", "precinct_name"}), None)
    precincts = sorted({(row.get(precinct_col) or "").strip() for row in rows}) if precinct_col else []
    precincts = [p for p in precincts if p]
    vote_mode_terms = {
        "election_day", "early_voting", "early", "absentee", "av_counting_boards",
        "provisional", "mail", "vote_by_mail", "uocava"
    }
    return {
        "file": item["name"],
        "download_url": item["download_url"],
        "rows": len(rows),
        "columns": columns,
        "distinct_precinct_labels": len(precincts),
        "vote_mode_columns": [c for c in columns if c.lower() in vote_mode_terms],
    }


def main() -> None:
    args = parse_args()
    repo = STATE_REPOS[args.state]
    outdir = Path(args.output)
    outdir.mkdir(parents=True, exist_ok=True)

    with httpx.Client(timeout=90, follow_redirects=True, headers={"User-Agent": "ElectionDataGrabber/0.1"}) as client:
        root = github_contents(client, repo, "")
        years = sorted([x["name"] for x in root if x.get("type") == "dir" and x["name"].isdigit()])
        latest = years[-1] if years else None
        records: list[dict] = []
        if latest:
            stack = [latest]
            while stack:
                path = stack.pop()
                try:
                    items = github_contents(client, repo, path)
                except httpx.HTTPStatusError:
                    continue
                for item in items:
                    if item.get("type") == "dir":
                        stack.append(item["path"])
                    elif item.get("type") == "file" and item["name"].lower().endswith(".csv"):
                        try:
                            records.append(inspect_csv(client, item))
                        except Exception as exc:
                            records.append({"file": item["name"], "error": repr(exc)})

    summary = {
        "state": args.state,
        "repo": repo,
        "latest_year": latest,
        "csv_files": len(records),
        "files_with_precincts": sum(1 for r in records if r.get("distinct_precinct_labels", 0) > 0),
        "files_with_vote_modes": sum(1 for r in records if r.get("vote_mode_columns")),
        "records": records,
    }
    (outdir / "census.json").write_text(json.dumps(summary, indent=2) + "\n")
    (outdir / "summary.md").write_text(
        f"# {args.state} state census\n\n"
        f"- Repository: `{repo}`\n"
        f"- Latest year found: `{latest}`\n"
        f"- CSV files inspected: **{summary['csv_files']}**\n"
        f"- Files with precinct labels: **{summary['files_with_precincts']}**\n"
        f"- Files with vote-mode columns: **{summary['files_with_vote_modes']}**\n"
    )


if __name__ == "__main__":
    main()
