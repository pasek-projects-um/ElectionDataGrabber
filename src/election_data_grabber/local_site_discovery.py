"""Validate fresh search leads for inspection without promoting source coverage."""

from datetime import datetime
from urllib.parse import urlsplit

from election_data_grabber.discovery_publication import publishable_url
from election_data_grabber.discovery_watch import ARTIFACT_PATH
from election_data_grabber.national_discovery import normalize

FIELDS = ["jurisdiction_id", "state", "url", "discovered_from", "evidence_excerpt",
          "observed_at", "evidence_status"]


def inspection_seeds(rows, localities):
    units = {row["jurisdiction_id"]: row for row in localities}
    seeds = {}
    rejected = 0
    for row in rows:
        unit = units.get(row.get("jurisdiction_id", ""))
        url = normalize(row.get("url", ""))
        source = normalize(row.get("discovered_from", ""))
        try:
            observed = datetime.fromisoformat(row.get("observed_at", "").replace("Z", "+00:00"))
            dated = observed.tzinfo is not None
        except ValueError:
            dated = False
        if (not unit or row.get("state") != unit["state"]
                or row.get("evidence_status") != "observed_link_candidate"
                or not row.get("evidence_excerpt", "").strip() or not dated
                or not url or not source or not publishable_url(url)
                or not publishable_url(source) or ARTIFACT_PATH.search(urlsplit(url).path)):
            rejected += 1
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
