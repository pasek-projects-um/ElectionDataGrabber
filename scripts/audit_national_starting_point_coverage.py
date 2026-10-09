"""Measure national starting-point coverage against state jurisdiction denominators.

A unit absent from the named jurisdiction registry is a coverage gap, not a
unit to which we can silently assign a state fallback URL.
"""
from __future__ import annotations

import csv
import json
from collections import Counter, defaultdict
from pathlib import Path

from scripts.build_national_where_to_look import build


def audit(registry: Path):
    candidates, gaps, _ = build(registry)
    with (registry / "us_primary_election_localities.csv").open(
            newline="", encoding="utf-8-sig") as stream:
        jurisdictions = list(csv.DictReader(stream))
    with (registry / "us_primary_election_locality_denominators.csv").open(
            newline="", encoding="utf-8-sig") as stream:
        denominators = list(csv.DictReader(stream))

    names = defaultdict(set)
    for item in jurisdictions:
        names[item["state"]].add(item["jurisdiction_id"])
    pages = defaultdict(list)
    for item in candidates:
        pages[item["jurisdiction_id"]].append(item)
    states = []
    for item in denominators:
        state = item["state"]
        expected = int(item["expected_primary_units"])
        identifiers = names[state]
        started = sum(bool(pages[jid]) for jid in identifiers)
        direct = sum(any(page["page_role"] != "state_directory_fallback"
                         for page in pages[jid]) for jid in identifiers)
        states.append({
            "state": state,
            "expected_units": expected,
            "named_units": len(identifiers),
            "units_with_any_start": started,
            "units_with_direct_lead": direct,
            "unnamed_units": max(0, expected - len(identifiers)),
            "named_units_without_start": len(identifiers) - started,
            "denominator_overrun": max(0, len(identifiers) - expected),
            "estimate_status": item["estimate_status"],
        })
    states.sort(key=lambda item: item["state"])
    keys = ("expected_units", "named_units", "units_with_any_start",
            "units_with_direct_lead", "unnamed_units",
            "named_units_without_start", "denominator_overrun")
    summary = {key: sum(item[key] for item in states) for key in keys}
    summary["state_count"] = len(states)
    summary["provisional_state_count"] = sum(
        item["estimate_status"] != "high_confidence" for item in states)
    summary["national_100_percent"] = (
        summary["unnamed_units"] == 0
        and summary["named_units_without_start"] == 0
        and summary["denominator_overrun"] == 0
        and summary["provisional_state_count"] == 0
        and len(names) == len(states)
    )
    return states, summary


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--registry", default="registry")
    parser.add_argument("--output", default="audit")
    args = parser.parse_args()
    states, summary = audit(Path(args.registry))
    output = Path(args.output)
    output.mkdir(parents=True, exist_ok=True)
    with (output / "national-starting-point-by-state.csv").open(
            "w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(states[0]))
        writer.writeheader()
        writer.writerows(states)
    (output / "national-starting-point-summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(summary, sort_keys=True))


if __name__ == "__main__":
    main()
