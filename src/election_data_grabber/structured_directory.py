"""Extract URLs from explicit CSV columns, retaining row and original-byte evidence."""

import csv
import hashlib
import io
from html import escape

from election_data_grabber.authority_directory import extract_directory
from election_data_grabber.discovery_publication import clean_public_label, publishable_url
from election_data_grabber.national_discovery import normalize


def extract_csv_directory(page_url, body, localities, *, state, name_column, url_column):
    if not any(u["state"] == state for u in localities):
        raise ValueError("No named units for the requested state")
    reader = csv.DictReader(io.StringIO(body.decode("utf-8-sig"), newline=""))
    if not reader.fieldnames or not {name_column, url_column} <= set(reader.fieldnames):
        raise ValueError("Missing explicit name or URL column")
    if name_column == url_column:
        raise ValueError("Name and URL columns must differ")
    digest = hashlib.sha256(body).hexdigest()
    candidates, matched = [], set()
    for number, row in enumerate(reader, start=2):
        if None in row or any(value is None for value in row.values()):
            raise ValueError(f"Malformed CSV row {number}")
        name, raw_url = row[name_column].strip(), row[url_column].strip()
        # Relative URLs and guessed domains in a spreadsheet are not observed website URLs.
        if not name or not raw_url.lower().startswith(("https://", "http://")):
            continue
        target = normalize(raw_url)
        if not target or not publishable_url(target):
            continue
        html = f'<tr><td>{escape(name)}</td><td><a href="{escape(target, quote=True)}">Website</a></td></tr>'
        rows, _ = extract_directory(page_url, html, localities, state=state)
        for candidate in rows:
            candidate.update(snapshot_sha256=digest, match_basis="csv_row",
                             evidence_excerpt=clean_public_label(name)[:300],
                             label=clean_public_label(name)[:300],
                             csv_row_number=number, name_column=name_column, url_column=url_column)
            candidates.append(candidate)
            if candidate["match_status"] == "unit_label_candidate" and candidate["link_role"] in {
                    "authority_website_lead", "external_website_lead", "result_page_lead"}:
                matched.add(candidate["associated_unit_ids"])
    unresolved = [{"jurisdiction_id": u["jurisdiction_id"], "state": state,
                   "jurisdiction_name": u["canonical_name"],
                   "next_action": "hunt_additional_authority_evidence",
                   "reason": "no_unambiguous_website_in_csv"}
                  for u in localities if u["state"] == state and u["jurisdiction_id"] not in matched]
    return candidates, unresolved
