"""Join national unit enumeration, starting pages and observed source leads offline.

Page provenance establishes a discovery path, never a verified service area.
Shared state fallback pages are scheduled once, not once per named locality.
"""

from __future__ import annotations

import argparse
import csv
import json
from collections import Counter, defaultdict
from pathlib import Path

from election_data_grabber.national_discovery import load_catalog, normalize
from scripts.audit_national_starting_point_coverage import audit
from scripts.build_national_where_to_look import build


def read(path):
    with path.open(newline="", encoding="utf-8-sig") as stream:
        return list(csv.DictReader(stream))


def parts(value):
    return {part.strip() for part in value.split("|") if part.strip()}


def compile_frontier(registry):
    pages, _, _ = build(registry)
    state_audit, starting_summary = audit(registry)
    localities = read(registry / "us_primary_election_localities.csv")
    catalog_path = registry / "discovered_result_sources.csv"
    catalog = read(catalog_path) if catalog_path.exists() else []
    by_unit, by_url = defaultdict(list), defaultdict(list)
    for page in pages:
        by_unit[page["jurisdiction_id"]].append(page)
        by_url[normalize(page["url"])].append(page)

    # Only exact observed page-to-page provenance; no host/name/state fuzzy joins.
    children = defaultdict(set)
    for source in catalog:
        for parent in parts(source["observed_from"]):
            children[normalize(parent)].add(normalize(source["url"]))

    units = []
    for unit in sorted(localities, key=lambda r: (r["state"], r["jurisdiction_id"])):
        starts = by_unit[unit["jurisdiction_id"]]
        direct = {normalize(p["url"]) for p in starts
                  if p["page_role"] != "state_directory_fallback"}
        fallback = {normalize(p["url"]) for p in starts
                    if p["page_role"] == "state_directory_fallback"}
        observed = set().union(*(children[url] for url in direct)) if direct else set()
        action = (
            "inspect_observed_result_leads" if observed else
            "extract_links_from_local_start" if direct else
            "resolve_local_authority_from_state_directory" if fallback else
            "find_official_starting_page"
        )
        units.append({
            "jurisdiction_id": unit["jurisdiction_id"], "state": unit["state"],
            "jurisdiction_level": unit["jurisdiction_level"],
            "jurisdiction_name": unit["canonical_name"],
            "direct_start_urls": " | ".join(sorted(direct)),
            "state_fallback_urls": " | ".join(sorted(fallback)),
            "observed_child_lead_urls": " | ".join(sorted(observed)),
            "next_action": action, "served_jurisdiction_verified": "false",
            "live_coverage": "false",
        })

    # Unique URL tasks retain every unit association without asserting service.
    tasks = []
    known_ids = {u["jurisdiction_id"] for u in units}
    for url, starts in sorted(by_url.items()):
        states = {p["state"] for p in starts}
        roles = {p["page_role"] for p in starts}
        directory = bool(roles & {"state_directory_fallback", "state_election_authority"})
        tasks.append({
            "url": url, "states": " | ".join(sorted(states)),
            "layer_priority": 1 if directory else 2,
            "page_roles": " | ".join(sorted(roles)),
            "associated_unit_ids": " | ".join(sorted({p["jurisdiction_id"] for p in starts
                                                       if p["jurisdiction_id"] in known_ids})),
            "next_action": "extract_authority_directory" if directory else "extract_result_links",
            "watch_signals": "new_result_links | election_selectors | iframe_targets | "
                             "script_or_embedded_endpoints | redirects | platform_fingerprints",
            "unpublished_feed_status": "unresolved_not_missing",
            "historical_recovery_sources": "official_result_archives | prior_election_links | "
                                           "Internet_Archive_captures",
            "observed_child_leads": len(children[url]),
            "evidence_registries": " | ".join(sorted({p["evidence_registry"] for p in starts})),
            "served_jurisdiction_verified": "false", "live_coverage": "false",
        })
    tasks.sort(key=lambda r: (r["layer_priority"], r["states"], r["url"]))
    source_tasks = []
    for source in sorted(catalog, key=lambda r: r["url"]):
        status, kind = source["target_status"], source["catalog_kind"]
        action = (
            "investigate_fetch_failure" if status in {"fetch_failed", "blocked_html"} else
            "inspect_result_artifact" if kind == "result_artifact_lead" else
            "extract_authority_links" if kind == "authority_cms" else
            "inspect_dashboard_and_payload_links" if kind == "dashboard_candidate" else
            "extract_result_links"
        )
        source_tasks.append({
            "source_id": source["source_id"], "url": source["url"],
            "layer_priority": 3,
            "states": source["states"], "catalog_kind": kind,
            "platform_families": source["platform_families"], "target_status": status,
            "observed_from": source["observed_from"], "next_action": action,
            "observed_years": source.get("observed_years", ""),
            "election_labels": source.get("election_labels", ""),
            "live_refresh_verification": "not_verified",
            "served_jurisdiction_verified": "false", "live_coverage": "false",
        })
    per_state = []
    for row in state_audit:
        state = row["state"]
        state_units = [u for u in units if u["state"] == state]
        state_sources = [s for s in source_tasks if state in parts(s["states"])]
        per_state.append({
            **row,
            "units_with_observed_child_leads": sum(bool(u["observed_child_lead_urls"])
                                                  for u in state_units),
            "units_using_state_fallback_only": sum(u["next_action"] ==
                "resolve_local_authority_from_state_directory" for u in state_units),
            "state_attributed_source_leads": len(state_sources),
            "unique_start_pages": sum(state in parts(t["states"]) for t in tasks),
            "enumeration_review_required": row["estimate_status"] != "high_confidence",
        })
    summary = {
        "starting_point_audit": starting_summary,
        "unit_next_actions": dict(sorted(Counter(u["next_action"] for u in units).items())),
        "unique_start_page_tasks": len(tasks),
        "observed_source_tasks": len(source_tasks),
        "source_next_actions": dict(sorted(Counter(s["next_action"] for s in source_tasks).items())),
        "scope": "Registry evidence only; exact page provenance is not verified service coverage.",
        "network_requests": 0,
        "watch_fingerprint_catalog": "registry/dashboard_fingerprints.json",
        "watch_fingerprint_catalog_version": load_catalog()["version"],
    }
    return units, tasks, source_tasks, per_state, summary


def write_rows(path, rows):
    if not rows:
        return
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--registry", type=Path, default=Path("registry"))
    parser.add_argument("--output", type=Path, default=Path("audit/national-layers"))
    args = parser.parse_args()
    units, starts, sources, states, summary = compile_frontier(args.registry)
    args.output.mkdir(parents=True, exist_ok=True)
    for name, rows in (("unit-next-actions.csv", units), ("unique-start-pages.csv", starts),
                       ("source-next-actions.csv", sources), ("layers-by-state.csv", states)):
        write_rows(args.output / name, rows)
    write_rows(args.output / "watch-fingerprints.csv", [
        {key: rule.get(key, "") for key in
         ("id", "family", "role", "field", "pattern", "specificity", "evidence")}
        for rule in load_catalog()["rules"]
    ])
    (args.output / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")
    print(json.dumps(summary, sort_keys=True))


if __name__ == "__main__":
    main()
