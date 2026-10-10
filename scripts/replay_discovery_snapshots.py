"""Reclassify captured HTML with the current catalog, without network access."""

import argparse
import csv
import hashlib
import json
from pathlib import Path

from election_data_grabber.national_discovery import (
    discover,
    html_access_state,
    load_catalog,
    run_batch,
    save,
)


def replay(captured, seeds, snapshots, output, *, max_depth=1, election="2026"):
    catalog = load_catalog()
    pages = {}
    for url, original in captured["pages"].items():
        page = dict(original)
        html_path = snapshots / (page.get("sha256", "") + ".html")
        if original["status"] == "fetched" and html_path.exists():
            html = html_path.read_bytes().decode("utf-8")
            if hashlib.sha256(html.encode()).hexdigest() != page["sha256"]:
                raise ValueError("Snapshot digest mismatch")
            page["access_state"] = html_access_state(html)
            page["candidates"] = discover(page["final_url"], html, url, catalog)
            if page["access_state"] == "blocked_html":
                page["status"] = "blocked_html"
                page["candidates"] = []
        pages[url] = page
    state = {
        "identity": hashlib.sha256(
            json.dumps([seeds, catalog, max_depth, election], sort_keys=True).encode()
        ).hexdigest(),
        "catalog_version": catalog["version"],
        "pages": pages,
        "publishers": {},
        "associations": [],
    }
    save(output, state)

    def no_network(url):
        raise AssertionError("Offline replay attempted a fetch")

    result = run_batch(
        seeds,
        output,
        no_network,
        max_publishers=200,
        max_requests=0,
        max_depth=max_depth,
        election=election,
    )
    result["summary"]["scope"] = (
        "Offline replay of captured HTML with current catalog; no network requests"
    )
    result["summary"]["captured_live_http_requests"] = captured.get("summary", {}).get(
        "http_requests_this_run", 0
    )
    save(output, result)
    return result


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--captured", type=Path, required=True)
    p.add_argument("--seeds", type=Path, required=True)
    p.add_argument("--snapshots", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    args = p.parse_args()
    with args.seeds.open(newline="", encoding="utf-8-sig") as f:
        seeds = list(csv.DictReader(f))
    result = replay(json.loads(args.captured.read_text()), seeds, args.snapshots, args.output)
    print(json.dumps(result["summary"], indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
