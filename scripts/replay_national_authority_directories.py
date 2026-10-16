"""Replay captured state pages and separate observed pages, hunting clues and mysteries."""

import argparse
import csv
import hashlib
import json
import re
from collections import Counter, defaultdict
from pathlib import Path

from election_data_grabber.authority_directory import extract_directory
from election_data_grabber.national_discovery import html_access_state, normalize
from election_data_grabber.source_context import source_context
from scripts.build_national_where_to_look import build

GOOD_ROLES = {"authority_website_lead", "external_website_lead", "result_page_lead"}


def read(path):
    with path.open(newline="", encoding="utf-8-sig") as stream:
        return list(csv.DictReader(stream))


def values(text):
    return {v.strip() for v in text.split("|") if v.strip()}


def replay(registry, captured, snapshots):
    units = read(registry / "us_primary_election_localities.csv")
    denominators = {r["state"]: r for r in read(
        registry / "us_primary_election_locality_denominators.csv")}
    directories = read(registry / "us_state_central_authority_sources.csv")
    candidates, states = [], []
    for directory in sorted(directories, key=lambda r: r["state"]):
        state = directory["state"]
        url = normalize(directory["central_authority_url"])
        page = captured.get("pages", {}).get(url, {})
        digest = page.get("snapshot_sha256", "")
        capture_available = bool(re.fullmatch(r"[a-f0-9]{64}", digest))
        capture_available = capture_available and (snapshots / (digest + ".html")).exists()
        rows = []
        access = "no_capture"
        if capture_available:
            body = (snapshots / (digest + ".html")).read_bytes()
            if hashlib.sha256(body).hexdigest() != digest:
                raise ValueError("Capture digest mismatch")
            access = html_access_state(body.decode("utf-8"))
            rows, _ = extract_directory(page.get("final_url", url), body.decode("utf-8"),
                                        units, state=state)
            for row in rows:
                row["captured_at"] = page.get("last_success_at", "")
                candidates.append(row)
        named = {u["jurisdiction_id"] for u in units if u["state"] == state}
        good = {r["associated_unit_ids"] for r in rows
                if r["match_status"] == "unit_label_candidate" and r["link_role"] in GOOD_ROLES}
        states.append({
            "state": state, "directory_url": url, "fetch_status": page.get("status", "not_checked"),
            "capture_available": capture_available, "capture_sha256": digest,
            "capture_access_state": access,
            "expected_primary_units": denominators[state]["expected_primary_units"],
            "denominator_status": denominators[state]["estimate_status"],
            "named_units": len(named), "extracted_links": len(rows),
            "units_with_unique_directory_hunting_clue": len(good),
            "units_without_unique_directory_hunting_clue": len(named - good),
        })
    starts, _, _ = build(registry)
    direct = defaultdict(set)
    for start in starts:
        if start["page_role"] != "state_directory_fallback":
            direct[start["jurisdiction_id"]].add(normalize(start["url"]))
    evidence = defaultdict(list)
    for row in candidates:
        if row["match_status"] == "unit_label_candidate" and row["link_role"] in GOOD_ROLES:
            evidence[row["associated_unit_ids"]].append(row)
    catalog = read(registry / "discovered_result_sources.csv")
    catalog_by_parent = defaultdict(list)
    catalog_by_url = {normalize(row["url"]): row for row in catalog}
    for row in catalog:
        if row["catalog_kind"] in {"dashboard_candidate", "results_page_lead"}:
            for parent in values(row["observed_from"]):
                catalog_by_parent[normalize(parent)].append(row)
    unit_rows = []
    for unit in sorted(units, key=lambda r: (r["state"], r["jurisdiction_id"])):
        jid = unit["jurisdiction_id"]
        clues = evidence[jid]
        hunts = direct[jid] | {row["url"] for row in clues}
        observed = set()
        linked = set()
        for parent in hunts:
            source_rows = catalog_by_parent[parent]
            if parent in catalog_by_url:
                source_rows = [*source_rows, catalog_by_url[parent]]
            for row in source_rows:
                if row["catalog_kind"] not in {"dashboard_candidate", "results_page_lead"}:
                    continue
                linked.add(row["url"])
                if row["target_status"] == "fetched":
                    observed.add(row["url"])
        bucket = "observed_result_page_candidate" if observed else (
            "evidence_backed_hunting_location" if hunts or linked else "unresolved_location")
        unit_rows.append({
            "jurisdiction_id": jid, "state": unit["state"], "unit_name": unit["canonical_name"],
            "bucket": bucket, "observed_result_page_urls": " | ".join(sorted(observed)),
            "linked_result_page_urls": " | ".join(sorted(linked)),
            "hunting_urls": " | ".join(sorted(hunts)),
            "directory_evidence_urls": " | ".join(sorted({r["observed_from"] for r in clues})),
            "directory_match_review_required": bool(clues),
            "next_action": "inspect_page_and_payload" if observed else
                           "review_clues_and_follow_links" if hunts or linked else
                           "resolve_authority_or_recover_historical_endpoint",
            "served_jurisdiction_verified": "false", "live_coverage": "false",
        })
    summary = {
        "state_pages": len(states), "fetch_statuses": dict(Counter(r["fetch_status"] for r in states)),
        "captured_state_pages": sum(r["capture_available"] for r in states),
        "usable_state_captures": sum(r["capture_access_state"] == "html_content" for r in states),
        "capture_access_states": dict(Counter(r["capture_access_state"] for r in states)),
        "extracted_links": len(candidates),
        "link_roles": dict(Counter(r["link_role"] for r in candidates)),
        "named_units": len(unit_rows), "unit_buckets": dict(Counter(r["bucket"] for r in unit_rows)),
        "network_requests_in_replay": 0, "service_associations_verified": 0,
        "scope": "Observed HTML candidates and unreviewed exact directory-label clues; no live-feed claim.",
    }
    return candidates, states, unit_rows, summary


def source_inventory(registry, candidates):
    """One row per evidence record, keeping source dimensions separate from unit buckets."""
    rows = []
    for row in read(registry / "discovered_result_sources.csv"):
        rows.append({"url": row["url"], "observed_from": row.get("observed_from", ""),
                     "evidence_layer": "discovery_catalog",
                     **source_context(row["url"], row.get("observed_years", "") + " " +
                                      row.get("election_labels", "")),
                     "target_status": row.get("target_status", "unknown"),
                     "live_coverage": "false"})
    for row in candidates:
        rows.append({"url": row["url"], "observed_from": row["observed_from"],
                     "evidence_layer": "authority_directory",
                     **source_context(row["url"], row["evidence_excerpt"]),
                     "target_status": "not_checked", "live_coverage": "false"})
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--registry", type=Path, default=Path("registry"))
    parser.add_argument("--watch-state", type=Path, required=True)
    parser.add_argument("--snapshots", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=Path("audit/authority-directory-national"))
    args = parser.parse_args()
    outputs = replay(args.registry, json.loads(args.watch_state.read_text()), args.snapshots)
    args.output.mkdir(parents=True, exist_ok=True)
    for name, rows in zip(("directory-link-candidates.csv", "capture-status-by-state.csv",
                           "unit-readiness.csv", "source-context.csv"),
                          (*outputs[:3], source_inventory(args.registry, outputs[0]))):
        if rows:
            with (args.output / name).open("w", newline="", encoding="utf-8") as stream:
                writer = csv.DictWriter(stream, fieldnames=list(rows[0]), lineterminator="\n")
                writer.writeheader()
                writer.writerows(rows)
    (args.output / "summary.json").write_text(json.dumps(outputs[3], indent=2, sort_keys=True) + "\n")
    print(json.dumps(outputs[3], sort_keys=True))


if __name__ == "__main__":
    main()
