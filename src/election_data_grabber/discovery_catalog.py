"""Catalog observed results leads without promoting source or live coverage."""

from __future__ import annotations

import csv
import hashlib
import re
from collections import Counter
from pathlib import Path
from urllib.parse import urlsplit

from election_data_grabber.discovery_publication import clean_public_candidate, clean_public_label
from election_data_grabber.national_discovery import RESULT, load_catalog, normalize, publisher_key

FIELDS = (
    "source_id",
    "url",
    "publisher_key",
    "catalog_kind",
    "platform_families",
    "score",
    "states",
    "source_scopes",
    "observed_years",
    "election_labels",
    "signatures",
    "target_status",
    "verification_status",
    "election_context_basis",
    "observed_from",
    "evidence_registries",
    "target_snapshot_sha256",
    "observed_at",
    "served_jurisdiction_verified",
    "live_coverage",
)


def catalog_sources(batches, *, observed_date):
    """batches: (checkpoint dict, seed rows). Keep exact origins, not inferred service areas."""
    rules = {r["id"]: r for r in load_catalog()["rules"]}
    records = {}
    for state, seeds in batches:
        origin_rows = {}
        for seed in seeds:
            origin_rows.setdefault(normalize(seed["url"]), []).append(seed)
        association_origins = {}
        for a in state.get("associations", []):
            association_origins.setdefault(a["candidate_url"], set()).add(a["seed_url"])
        final_pages = {
            normalize(p.get("final_url", "")): p
            for p in state["pages"].values()
            if p.get("status") == "fetched"
        }
        for publisher in state["publishers"].values():
            for candidate in publisher["candidates"].values():
                candidate = clean_public_candidate(candidate)
                if candidate is None:
                    continue
                url = normalize(candidate["url"])
                if not url or urlsplit(url).path.lower().endswith((".js", ".css")):
                    continue
                roles = set(candidate["roles"])
                provenance = candidate["provenance"]
                keyword = any(p["keyword_match"] for p in provenance)
                parent_results = any(RESULT.search(p["page_url"]) for p in provenance)
                if "result_platform" in roles:
                    kind = "dashboard_candidate"
                elif "report_family" in roles and (keyword or parent_results):
                    kind = "result_artifact_lead"
                elif "authority_discovery" in roles:
                    kind = "authority_cms"
                elif keyword:
                    kind = "results_page_lead"
                else:
                    continue
                # Vendor JS assets provide platform evidence, not independent sources.
                if all(p["kind"] == "script" for p in provenance):
                    continue
                r = records.setdefault(
                    url,
                    {
                        "source_id": "discovered:" + hashlib.sha256(url.encode()).hexdigest()[:16],
                        "url": url,
                        "publisher_key": publisher_key(url),
                        "catalog_kind": kind,
                        "platform_families": set(),
                        "score": 0,
                        "states": set(),
                        "source_scopes": set(),
                        "observed_years": set(),
                        "election_labels": set(),
                        "signatures": set(),
                        "target_status": "not_fetched",
                        "verification_status": "candidate",
                        "election_context_basis": set(),
                        "observed_from": set(),
                        "evidence_registries": set(),
                        "target_snapshot_sha256": "",
                        "observed_at": observed_date,
                        "served_jurisdiction_verified": "false",
                        "live_coverage": "false",
                    },
                )
                r["score"] = max(r["score"], candidate["score"])
                r["signatures"].update(candidate["signatures"])
                r["platform_families"].update(
                    rules[s]["family"] for s in candidate["signatures"] if s in rules
                )
                r["election_context_basis"].add(
                    "link_or_target_keyword"
                    if keyword
                    else "parent_results_page"
                    if parent_results
                    else "platform_signature_only"
                )
                for p in provenance:
                    page = normalize(p["page_url"])
                    r["observed_from"].add(page)
                    label = clean_public_label(p["label"]) if p["kind"] != "response" else ""
                    if label:
                        r["election_labels"].add(label[:200])
                    # Years describe observed URL/label strings, not an asserted election date.
                    r["observed_years"].update(
                        re.findall(r"(?<!\d)(?:19|20)\d{2}(?!\d)", url + " " + label)
                    )
                    # Redirected pages map back to the registered requested URL.
                    requested = [
                        u
                        for u, v in state["pages"].items()
                        if normalize(v.get("final_url", "")) == page
                    ]
                    for origin in [page, *requested, *association_origins.get(url, set())]:
                        for seed in origin_rows.get(origin, []):
                            r["states"].add(seed.get("state", ""))
                            r["source_scopes"].add(seed.get("page_role", "unknown"))
                            r["evidence_registries"].add(seed.get("evidence_registry", ""))
                page = state["pages"].get(url) or final_pages.get(url)
                # Keep an earlier successful fetch when a later independent request fails.
                if page and (page["status"] == "fetched" or r["target_status"] != "fetched"):
                    r["target_status"] = page["status"]
                    r["target_snapshot_sha256"] = page.get("sha256", "")
                    r["observed_at"] = page.get("observed_at", observed_date)
                    r["verification_status"] = (
                        "fetched_unverified" if page["status"] == "fetched" else page["status"]
                    )
    rows = []
    for r in records.values():
        rows.append(
            {k: " | ".join(sorted(v - {""})) if isinstance(v, set) else v for k, v in r.items()}
        )
    return sorted(rows, key=lambda r: (r["catalog_kind"], -r["score"], r["url"]))


def write_catalog(rows, path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=FIELDS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    return {
        "cataloged_urls": len(rows),
        "publisher_keys": len({r["publisher_key"] for r in rows}),
        "kinds": dict(Counter(r["catalog_kind"] for r in rows)),
        "target_statuses": dict(Counter(r["target_status"] for r in rows)),
        "state_attributed_records": sum(bool(r["states"]) for r in rows),
        "states_with_attributed_records": sorted(
            {s for r in rows for s in r["states"].split(" | ") if s}
        ),
        "verified_live_sources": 0,
    }
