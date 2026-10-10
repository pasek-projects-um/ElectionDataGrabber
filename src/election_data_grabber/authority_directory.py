"""Extract observed directory links against named units without certifying service."""

from __future__ import annotations

import hashlib
import re
import unicodedata
from urllib.parse import urlsplit

from bs4 import BeautifulSoup

from election_data_grabber.discovery_publication import clean_public_label, publishable_url
from election_data_grabber.national_discovery import html_access_state, normalize

AUTHORITY = re.compile(r"\b(elections?|clerk|registrar|board|county|parish|municipal|town|city)\b",
                       re.IGNORECASE)
ARTIFACT = re.compile(r"\.(pdf|csv|xlsx?|docx?|zip|xml|json)$", re.IGNORECASE)
SOCIAL = {"facebook.com", "twitter.com", "x.com", "instagram.com", "youtube.com"}
FIELDS = ("state", "url", "observed_from", "resolution_base", "associated_unit_ids",
          "match_status", "match_basis", "label", "evidence_excerpt", "snapshot_sha256",
          "next_action", "served_jurisdiction_verified", "live_coverage")


def words(text):
    text = unicodedata.normalize("NFKD", text).casefold()
    return " ".join(re.findall(r"[a-z0-9]+", text))


def unit_matches(text, units):
    normalized = " " + words(text) + " "
    matches = [(unit, words(unit["canonical_name"])) for unit in units
               if words(unit["canonical_name"]) and
               " " + words(unit["canonical_name"]) + " " in normalized]
    # 'York' inside 'New York' is not a second directory entry. Equal names
    # remain ambiguous when separate units share them.
    return [unit for unit, name in matches if not any(
        name != longer and " " + name + " " in " " + longer + " "
        for _, longer in matches)]


def extract_directory(page_url, html, localities, *, state):
    units = [u for u in localities if u["state"] == state]
    if not units:
        raise ValueError("No named units for the requested state")
    page_url = normalize(page_url)
    if not page_url or not publishable_url(page_url):
        raise ValueError("Invalid directory page URL")
    access = html_access_state(html)
    if access in {"blocked_html", "application_shell"}:
        return [], [{"jurisdiction_id": u["jurisdiction_id"], "state": state,
                     "jurisdiction_name": u["canonical_name"],
                     "next_action": "resolve_directory_access", "reason": access} for u in units]
    soup = BeautifulSoup(html, "html.parser")
    base = soup.find("base", href=True)
    resolution_base = normalize(base["href"], page_url) if base else page_url
    resolution_base = resolution_base or page_url
    snapshot = hashlib.sha256(html.encode()).hexdigest()
    records, matched = {}, set()
    for anchor in soup.find_all("a", href=True):
        target = normalize(anchor["href"], resolution_base)
        if not target or not publishable_url(target):
            continue
        host = urlsplit(target).hostname or ""
        if any(host == site or host.endswith("." + site) for site in SOCIAL):
            continue
        label = anchor.get_text(" ", strip=True)
        match = unit_matches(label, units)
        basis, context = "anchor_label", label
        if not match:
            row = anchor.find_parent(["tr", "li"])
            if row:
                context = row.get_text(" ", strip=True)
                # Avoid promoting a whole navigation tree as a single entry.
                if len(context) <= 1000:
                    match = unit_matches(context, units)
                    basis = "directory_row"
        if not match and not AUTHORITY.search(label + " " + urlsplit(target).path):
            continue
        ids = sorted({u["jurisdiction_id"] for u in match})
        artifact = bool(ARTIFACT.search(urlsplit(target).path))
        anchor_only = str(anchor["href"]).startswith("#") or target == page_url
        status = ("directory_anchor" if anchor_only else "artifact_lead" if artifact else "unit_label_candidate" if len(ids) == 1
                  else "ambiguous_unit_label" if ids else "unmatched_directory_link")
        if status == "unit_label_candidate":
            matched.update(ids)
        key = (target, tuple(ids), status)
        record = {
            "state": state, "url": target, "observed_from": page_url,
            "resolution_base": resolution_base,
            "associated_unit_ids": " | ".join(ids),
            "match_status": status, "match_basis": basis if ids else "authority_keyword",
            "label": clean_public_label(label)[:300],
            "evidence_excerpt": clean_public_label(context)[:1000],
            "snapshot_sha256": snapshot,
            "next_action": "review_unit_and_authority_association" if len(ids) == 1
                           and not artifact and not anchor_only else "review_ambiguous_or_unmapped_link",
            "served_jurisdiction_verified": "false", "live_coverage": "false",
        }
        records.setdefault(key, record)
    unresolved = [{"jurisdiction_id": u["jurisdiction_id"], "state": state,
                   "jurisdiction_name": u["canonical_name"],
                   "next_action": "hunt_additional_authority_evidence",
                   "reason": "no_unambiguous_website_label_in_this_capture"}
                  for u in units if u["jurisdiction_id"] not in matched]
    return sorted(records.values(), key=lambda r: (r["url"], r["associated_unit_ids"])), unresolved
