"""Validate fresh search leads for inspection without promoting source coverage."""

import hashlib
import json
from datetime import datetime
from urllib.parse import urlsplit

from election_data_grabber.discovery_publication import publishable_url
from election_data_grabber.discovery_watch import ARTIFACT_PATH
from election_data_grabber.national_discovery import normalize

FIELDS = ["jurisdiction_id", "state", "url", "discovered_from", "evidence_excerpt",
          "observed_at", "evidence_status"]
QUARANTINE_FIELDS = ["input_row", "jurisdiction_id", "state", "reason", "url",
                     "evidence_url", "row_sha256"]


def inspection_seeds(rows, localities, *, rejected_rows=None):
    units = {row["jurisdiction_id"]: row for row in localities}
    seeds = {}
    rejected = 0
    for number, original in enumerate(rows, start=2):
        row = {key: value if isinstance(value, str) else ""
               for key, value in original.items()}
        unit = units.get(row.get("jurisdiction_id", ""))
        url = normalize(row.get("url", ""))
        source = normalize(row.get("discovered_from", ""))
        try:
            observed = datetime.fromisoformat(row.get("observed_at", "").replace("Z", "+00:00"))
            dated = observed.tzinfo is not None
        except ValueError:
            dated = False
        reason = next((reason for invalid, reason in [
            (not unit, "unknown_jurisdiction"),
            (bool(unit) and row.get("state") != unit["state"], "state_mismatch"),
            (row.get("evidence_status") != "observed_link_candidate", "invalid_evidence_status"),
            (not row.get("evidence_excerpt", "").strip(), "missing_evidence"),
            (not dated, "invalid_observation_time"),
            (not url or not publishable_url(url), "unsafe_or_unsupported_url"),
            (not source or not publishable_url(source), "unsafe_or_unsupported_evidence_url"),
            (bool(ARTIFACT_PATH.search(urlsplit(url).path)), "artifact_requires_inspection"),
        ] if invalid), "")
        if reason:
            rejected += 1
            if rejected_rows is not None:
                digest = hashlib.sha256(json.dumps(
                    {str(k): v for k, v in original.items()}, sort_keys=True).encode()).hexdigest()
                rejected_rows.append({
                    "input_row": number, "jurisdiction_id": unit["jurisdiction_id"] if unit else "",
                    "state": unit["state"] if unit else "", "reason": reason,
                    "url": url if url and publishable_url(url) else "[withheld]",
                    "evidence_url": source if source and publishable_url(source) else "[withheld]",
                    "row_sha256": digest,
                })
            continue
        key = (url, unit["jurisdiction_id"], source)
        seeds[key] = {
            "url": url, "states": unit["state"],
            "associated_unit_ids": unit["jurisdiction_id"],
            "page_roles": "fresh_search_inspection_lead", "observed_from": source,
            "evidence_excerpt": row["evidence_excerpt"], "observed_at": row["observed_at"],
            "served_jurisdiction_verified": "false", "live_coverage": "false",
        }
    return [seeds[key] for key in sorted(seeds)], rejected
