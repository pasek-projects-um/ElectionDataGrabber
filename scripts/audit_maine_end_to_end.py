from __future__ import annotations

import argparse
import csv
import json
import re
from dataclasses import asdict
from pathlib import Path
from urllib.parse import urlparse

import httpx
from bs4 import BeautifulSoup

from election_data_grabber.adapters.archive_discovery import discover_election_artifacts
from election_data_grabber.adapters.pdf_extract import extract_pdf_text, pdf_needs_fallback, pdf_image_fallback_profile
from election_data_grabber.artifact_auditor import (
    ArtifactAudit,
    AuditStatus,
    needs_escalation,
    provisional_portability,
)
from election_data_grabber.authority_resolver import discover_candidate_links
from election_data_grabber.adapters.dynamic_documents import fingerprint_dynamic_document

UNIT_RE = re.compile(
    r"\b(?:ward|precinct|district|voting\s+district|polling\s+place|reporting\s+unit)"
    r"\s*(?:no\.?\s*)?([A-Z0-9][A-Z0-9._-]{0,15})",
    re.I,
)
CONTEST_RE = re.compile(
    r"\b(?:president|governor|senator|representative|council|school\s+board|"
    r"select\s*board|referendum|question|mayor|clerk|treasurer)\b",
    re.I,
)
NUMBER_RE = re.compile(r"\b\d{1,3}(?:,\d{3})*\b")


def root_url(url: str) -> str:
    p = urlparse(url)
    return f"{p.scheme}://{p.netloc}/" if p.scheme and p.netloc else url


def text_metrics(text: str) -> tuple[int, int, int]:
    units = {m.group(0).strip().lower() for m in UNIT_RE.finditer(text)}
    contests = len({m.group(0).lower() for m in CONTEST_RE.finditer(text)})
    numeric = len(NUMBER_RE.findall(text))
    return len(units), contests, numeric


def audit_pdf(url: str, body: bytes) -> ArtifactAudit:
    try:
        extracted = extract_pdf_text(body)
    except Exception as exc:
        return ArtifactAudit(
            url, AuditStatus.UNREADABLE, has_text_layer=False,
            warnings=[f"pdf_extract_error:{type(exc).__name__}"]
        )
    units, contests, numeric = text_metrics(extracted.text)
    has_text = sum(p.text_chars for p in extracted.pages) >= 100
    if not has_text:
        profile = pdf_image_fallback_profile(body)
        status = AuditStatus.UNREADABLE
        if profile.get("ocr_candidate"):
            extracted.warnings.append("ocr_required_unvalidated")
            extracted.warnings.append("provisional_E_until_ocr_reconciles")
    elif units and contests and numeric >= 4:
        status = AuditStatus.PARSED
    elif contests or numeric >= 8:
        status = AuditStatus.PARTIAL
    else:
        status = AuditStatus.STRUCTURALLY_UNRESOLVED
    return ArtifactAudit(
        url,
        status,
        result_rows=numeric,
        reporting_units=units,
        contests=contests,
        candidates=0,
        has_text_layer=has_text,
        warnings=list(extracted.warnings) + (["pdf_fallback_recommended"] if pdf_needs_fallback(extracted) else []),
    )


def audit_html(url: str, body: bytes) -> ArtifactAudit:
    soup = BeautifulSoup(body, "html.parser")
    text = soup.get_text(" ", strip=True)
    units, contests, numeric = text_metrics(text)
    tables = soup.find_all("table")
    numeric_rows = 0
    for tr in soup.find_all("tr"):
        row = " ".join(x.get_text(" ", strip=True) for x in tr.find_all(["th", "td"]))
        if NUMBER_RE.search(row):
            numeric_rows += 1
    semantic_blocks = 0
    for node in soup.find_all(["p","li","div","section","article"]):
        block = node.get_text(" ", strip=True)
        if CONTEST_RE.search(block) and NUMBER_RE.search(block):
            semantic_blocks += 1
    if units and contests and numeric_rows:
        status = AuditStatus.PARSED
    elif tables and numeric_rows:
        status = AuditStatus.PARTIAL
    elif semantic_blocks >= 2 or (contests and numeric >= 4):
        status = AuditStatus.PARTIAL
    else:
        status = AuditStatus.STRUCTURALLY_UNRESOLVED
    return ArtifactAudit(
        url,
        status,
        result_rows=max(numeric_rows, numeric),
        reporting_units=units,
        contests=contests,
        has_text_layer=True,
        warnings=[] if tables else (["semantic_html_results"] if semantic_blocks else ["no_html_tables"]),
    )


def fetch(client: httpx.Client, url: str):
    r = client.get(url)
    r.raise_for_status()
    return r


def resolve_authority(client: httpx.Client, locality: str, seed: str) -> tuple[str | None, bytes | None, list[str]]:
    warnings = []
    for url in dict.fromkeys([seed, root_url(seed)]):
        try:
            r = fetch(client, url)
            if str(r.url) != url:
                warnings.append(f"redirect:{url}->{r.url}")
            return str(r.url), r.content, warnings
        except Exception as exc:
            warnings.append(f"fetch_fail:{url}:{type(exc).__name__}")
    return None, None, warnings


def audit_locality(client: httpx.Client, row: dict[str, str], max_artifacts: int) -> list[dict]:
    locality, county, seed = row["locality"], row["county"], row["authority_url"]
    resolved, body, warnings = resolve_authority(client, locality, seed)
    if not resolved or body is None:
        return [{
            "locality": locality, "county": county, "authority_seed": seed,
            "resolved_authority": "", "artifact_url": "", "artifact_kind": "",
            "audit_status": "authority_unresolved", "result_rows": 0,
            "reporting_units": 0, "contests": 0, "has_text_layer": "",
            "provisional_portability": "pending", "needs_escalation": True,
            "warnings": ";".join(warnings),
        }]

    artifacts = discover_election_artifacts(body, resolved)
    if not artifacts:
        # Crawl high-scoring election links from the reachable authority/home page.
        html = body.decode("utf-8", errors="ignore")
        candidates = discover_candidate_links(resolved, html)[:5]
        for candidate in candidates:
            try:
                cr = fetch(client, candidate.url)
                artifacts.extend(discover_election_artifacts(cr.content, str(cr.url)))
                if artifacts:
                    break
            except Exception as exc:
                warnings.append(f"candidate_fail:{candidate.url}:{type(exc).__name__}")

    # De-duplicate and favor concrete documents over generic web links.
    uniq = {}
    priority = {"csv": 0, "spreadsheet": 1, "pdf": 2, "dynamic_document": 3, "web": 4, "other": 5}
    for a in artifacts:
        uniq[a.url] = a
    selected = sorted(uniq.values(), key=lambda a: (priority.get(a.kind, 9), a.url))[:max_artifacts]

    if not selected:
        return [{
            "locality": locality, "county": county, "authority_seed": seed,
            "resolved_authority": resolved, "artifact_url": "", "artifact_kind": "",
            "audit_status": "no_artifact_found", "result_rows": 0,
            "reporting_units": 0, "contests": 0, "has_text_layer": "",
            "provisional_portability": "C", "needs_escalation": True,
            "warnings": ";".join(warnings),
        }]

    out = []
    for art in selected:
        try:
            r = fetch(client, art.url)
            ctype = (r.headers.get("content-type") or "").lower()
            if art.kind == "pdf" or "application/pdf" in ctype or str(r.url).lower().endswith(".pdf"):
                audit = audit_pdf(str(r.url), r.content)
            elif art.kind == "dynamic_document":
                platform = fingerprint_dynamic_document(str(r.url), r.content) or "dynamic_document"
                audit = ArtifactAudit(
                    str(r.url), AuditStatus.PARTIAL, result_rows=1, has_text_layer=True,
                    warnings=[f"generic_family:{platform}"]
                )
            elif art.kind in {"csv", "spreadsheet"}:
                # Structured downloadable artifacts are configuration/profile work
                # even before full field normalization.
                audit = ArtifactAudit(str(r.url), AuditStatus.PARTIAL, result_rows=1, has_text_layer=True,
                                      warnings=[f"structured_artifact:{art.kind}"])
            else:
                audit = audit_html(str(r.url), r.content)
            out.append({
                "locality": locality, "county": county, "authority_seed": seed,
                "resolved_authority": resolved, "artifact_url": audit.source_url,
                "artifact_kind": art.kind, "audit_status": audit.status.value,
                "result_rows": audit.result_rows, "reporting_units": audit.reporting_units,
                "contests": audit.contests, "has_text_layer": audit.has_text_layer,
                "provisional_portability": provisional_portability(audit),
                "needs_escalation": needs_escalation(audit),
                "warnings": ";".join(warnings + audit.warnings),
            })
        except Exception as exc:
            out.append({
                "locality": locality, "county": county, "authority_seed": seed,
                "resolved_authority": resolved, "artifact_url": art.url,
                "artifact_kind": art.kind, "audit_status": "artifact_fetch_failed",
                "result_rows": 0, "reporting_units": 0, "contests": 0,
                "has_text_layer": "", "provisional_portability": "pending",
                "needs_escalation": True,
                "warnings": ";".join(warnings + [f"artifact_fail:{type(exc).__name__}"]),
            })
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--registry", type=Path, default=Path("registry/me_locality_authorities.csv"))
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--summary", type=Path, required=True)
    ap.add_argument("--shard", type=int, default=0)
    ap.add_argument("--shards", type=int, default=1)
    ap.add_argument("--max-artifacts", type=int, default=2)
    args = ap.parse_args()

    with args.registry.open(encoding="utf-8-sig") as f:
        all_rows = list(csv.DictReader(f))
    rows = [r for i, r in enumerate(all_rows) if i % args.shards == args.shard]

    audits = []
    with httpx.Client(
        timeout=httpx.Timeout(10.0, connect=6.0),
        follow_redirects=True,
        headers={"User-Agent": "ElectionDataGrabber/0.1 (+academic election research)"},
    ) as client:
        for i, row in enumerate(rows, 1):
            result = audit_locality(client, row, args.max_artifacts)
            audits.extend(result)
            print(f"[{i}/{len(rows)}] {row['locality']} -> {[(x['audit_status'], x['provisional_portability']) for x in result]}")

    fields = [
        "locality","county","authority_seed","resolved_authority","artifact_url","artifact_kind",
        "audit_status","result_rows","reporting_units","contests","has_text_layer",
        "provisional_portability","needs_escalation","warnings",
    ]
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields); w.writeheader(); w.writerows(audits)

    locality_best = {}
    rank = {"A":0,"B":1,"C":2,"D":3,"E":4,"pending":9}
    for x in audits:
        cur = locality_best.get(x["locality"])
        if cur is None or rank.get(x["provisional_portability"],9) < rank.get(cur,9):
            locality_best[x["locality"]] = x["provisional_portability"]
    summary = {
        "shard": args.shard, "shards": args.shards, "localities": len(rows),
        "artifact_audits": len(audits),
        "authority_resolved": len({x["locality"] for x in audits if x["resolved_authority"]}),
        "artifact_found": len({x["locality"] for x in audits if x["artifact_url"]}),
        "reporting_units_detected": sum(int(x["reporting_units"] or 0) for x in audits),
        "portability": {k: sum(v == k for v in locality_best.values()) for k in ["A","B","C","D","E","pending"]},
        "escalations": sum(bool(x["needs_escalation"]) for x in audits),
    }
    args.summary.write_text(json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")
    print("SUMMARY", json.dumps(summary, sort_keys=True))


if __name__ == "__main__":
    main()
