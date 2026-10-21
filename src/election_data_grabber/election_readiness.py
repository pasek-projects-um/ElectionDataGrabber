"""Reproducible election-night release evidence, with separate coverage denominators."""

from __future__ import annotations

import csv
import hashlib
from collections import defaultdict
from pathlib import Path

from election_data_grabber.election_night import report
from election_data_grabber.local_site_discovery import inspection_seeds
from election_data_grabber.national_discovery import normalize


def read(path):
    with Path(path).open(newline="", encoding="utf-8-sig") as stream:
        return list(csv.DictReader(stream))


def readiness(registry, manifest, state_dir, *, now=None):
    registry = Path(registry)
    localities = read(registry / "us_primary_election_localities.csv")
    units = {row["jurisdiction_id"]: row for row in localities}
    if len(units) != len(localities):
        raise ValueError("Duplicate canonical locality identity")
    denominators = read(registry / "us_primary_election_locality_denominators.csv")
    if len({row["state"] for row in denominators}) != len(denominators):
        raise ValueError("Duplicate state denominator")
    central = {
        row["state"]
        for row in read(registry / "us_state_central_authority_sources.csv")
        if normalize(row["central_authority_url"])
    }
    seeds, rejected = inspection_seeds(
        read(registry / "local_site_discovery_leads.csv"), localities
    )
    leads = {row["associated_unit_ids"] for row in seeds}
    direct = {
        jid
        for jid, row in units.items()
        if any(
            normalize(row.get(field, ""))
            for field in ("final_evidence_url", "election_night_evidence_url")
        )
    }
    verified = set()
    for row in read(registry / "jurisdiction_source_capabilities.csv"):
        jid = row["jurisdiction_id"]
        if (
            jid in units
            and row["verification_status"] == "verified"
            and row["capability_type"] == "election_night"
            and normalize(row["source_url"])
        ):
            verified.add(jid)
    by_state = defaultdict(set)
    for jid, unit in units.items():
        by_state[unit["state"]].add(jid)
    states = []
    for denominator in sorted(denominators, key=lambda row: row["state"]):
        state = denominator["state"]
        ids = by_state[state]
        expected = int(denominator["expected_primary_units"])
        starts = {jid for jid in ids if jid in direct or state in central}
        candidates = (direct | leads) & ids
        states.append(
            {
                "state": state,
                "expected_units": expected,
                "named_units": len(ids),
                "denominator_status": denominator["estimate_status"],
                "unnamed_units": max(0, expected - len(ids)),
                "denominator_overrun": max(0, len(ids) - expected),
                "units_with_any_start": len(starts),
                "units_with_core_direct_evidence": len(direct & ids),
                "units_with_search_candidates": len(leads & ids),
                "units_with_any_direct_candidate": len(candidates),
                "fallback_only_units": len(starts - candidates),
                "historically_verified_election_night_capability_units": len(verified & ids),
            }
        )
    summary = (
        {
            key: sum(row[key] for row in states)
            for key in states[0]
            if isinstance(states[0][key], int)
        }
        if states
        else {}
    )
    summary.update(
        state_count=len(states),
        provisional_state_count=sum(
            row["denominator_status"] != "high_confidence" for row in states
        ),
        rejected_search_leads=rejected,
    )
    collector = report(manifest, state_dir, now=now)
    blockers = []
    if not collector["enabled_feeds"]:
        blockers.append("No reviewed election-specific feeds are enabled")
    if collector["stale_enabled_feeds"]:
        blockers.append("Selected feeds lack a fresh accepted capture")
    if any(feed["enabled"] and feed["status"] != "ok" for feed in collector["feeds"]):
        blockers.append("One or more enabled feeds require operator review")
    if summary["provisional_state_count"]:
        blockers.append("National jurisdiction denominators remain provisional")
    if collector["refresh_verified_feeds"] < collector["enabled_feeds"]:
        blockers.append("Selected feeds lack reviewed current-election refresh evidence")
    blockers.append("Persistent worker deployment and monitoring require independent evidence")
    fingerprints = {
        name: hashlib.sha256((registry / name).read_bytes()).hexdigest()
        for name in (
            "us_primary_election_localities.csv",
            "us_primary_election_locality_denominators.csv",
            "us_state_central_authority_sources.csv",
            "local_site_discovery_leads.csv",
            "jurisdiction_source_capabilities.csv",
        )
    }
    return {
        "input_sha256": fingerprints,
        "scope": "National discovery evidence and selected-feed operations are separate measures",
        "national": summary,
        "states": states,
        "collector": collector,
        "blockers": blockers,
        "national_ready": False,
        "population_weighted_coverage": None,
        "reporting_place_weighted_coverage": None,
        "unknown_weights_reason": "No adjudicated deduplicated weight/source mapping supplied",
        "capability_note": "Historical registry adjudication is not current endpoint reachability",
    }
