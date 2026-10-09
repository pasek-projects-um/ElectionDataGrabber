"""Remove transient access URLs and personal contact labels from published discovery evidence."""

from __future__ import annotations

import re
from urllib.parse import parse_qsl, unquote, urlsplit

EMAIL = re.compile(r"(?<![A-Za-z0-9._%+-])[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
PRIVATE_KEYS = re.compile(
    r"(?:token|session|auth|signature|ticket|saml|email|challenge|__cf_|captcha)", re.IGNORECASE
)


SAFE_QUERY_KEYS = {
    "erselectionid",
    "eid",
    "officeinelectionid",
    "officeinelectionidlist",
    "archived",
    "scenario",
    "sc_lang",
    "election",
    "electionid",
    "election_id",
    "electionyear",
    "electiondate",
    "year",
    "county",
    "countyid",
    "county_id",
    "state",
    "precinct",
    "precinctid",
    "precinct_id",
    "contest",
    "contestid",
    "contest_id",
    "race",
    "raceid",
    "race_id",
    "office",
    "officeid",
    "office_id",
    "district",
    "districtid",
    "district_id",
    "language",
    "lang",
    "view",
    "mode",
    "format",
    "page",
}


def publishable_url(url):
    decoded = unquote(url)
    if EMAIL.search(decoded):
        return False
    parsed = urlsplit(url)
    if "/cdn-cgi/" in parsed.path or (parsed.hostname or "").endswith(
        ("cloudflare.com", "perimeterx.net", "perfdrive.com")
    ):
        return False
    for key, value in parse_qsl(parsed.query, keep_blank_values=True):
        if (
            key.casefold() not in SAFE_QUERY_KEYS
            or PRIVATE_KEYS.search(key)
            or len(value) > 160
            or re.fullmatch(r"[A-Za-z0-9_-]{40,}", value)
        ):
            return False
    return True


def clean_public_label(label):
    return EMAIL.sub("[email omitted]", " ".join(label.split()))


def clean_public_candidate(candidate):
    if not publishable_url(candidate["url"]):
        return None
    provenance = []
    for original in candidate["provenance"]:
        if not all(
            publishable_url(original.get(key, ""))
            for key in ("page_url", "raw_target", "resolution_base")
        ):
            continue
        row = dict(original)
        row["label"] = clean_public_label(row.get("label", ""))
        provenance.append(row)
    if not provenance:
        return None
    return dict(candidate, provenance=provenance)
