from __future__ import annotations

import csv
from pathlib import Path
from urllib.parse import urlparse


def read_rows(path: Path) -> list[dict[str,str]]:
    with path.open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def classify_family(url: str) -> tuple[str,str]:
    host=(urlparse(url).hostname or "").lower()
    path=urlparse(url).path.lower()
    if "clarityelections.com" in host:
        return "clarity","clarity"
    if "/results/public/" in path:
        return "results_portal",""
    if "electionresults." in host or "results." in host or host.startswith("enr."):
        return "results_portal",""
    if path.endswith(".csv") or "export" in path or "mediafiles" in path:
        return "tabular_export","generic_csv"
    if path.endswith((".xlsx",".xls")):
        return "tabular_export","generic_excel"
    if path.endswith(".pdf"):
        return "document","pdf_extract"
    if host.endswith(".gov") or ".gov." in host or host.endswith(".us"):
        return "official_web",""
    return "unknown",""


def source_candidates(root: Path) -> list[dict[str,str]]:
    inputs=[
        ("medsl", root/"audit/medsl_2024_source_leads.csv", "source_url"),
        ("nyt", root/"audit/nyt_2024_state_source_coverage.csv", "source_url"),
        ("downballotr", root/"audit/downballotr_official_source_leads.csv", "source_url"),
        ("internal", root/"registry/first_pass_state_result_surfaces.csv", "result_url"),
    ]
    out=[]
    seen=set()
    for origin,path,url_field in inputs:
        for row in read_rows(path):
            url=row.get(url_field,"").strip()
            if not url or not url.startswith(("http://","https://")):
                continue
            key=(row["state"],url)
            if key in seen:
                continue
            seen.add(key)
            family,parser=classify_family(url)
            runnable=parser in {"clarity","generic_csv","generic_excel","pdf_extract"}
            out.append({
                "state":row["state"],
                "source_url":url,
                "source_origin":origin,
                "verification_status":"candidate",
                "fetch_status":"untested",
                "platform_family":family,
                "parser_family":parser,
                "execution_stage":"adapter_candidate" if runnable else ("classified" if parser else "needs_family_probe"),
                "notes":"existing_adapter_family" if runnable else "",
            })
    return sorted(out,key=lambda r:(r["state"],r["source_origin"],r["source_url"]))


def main() -> None:
    root=Path(__file__).resolve().parents[1]
    rows=source_candidates(root)
    out=root/"audit/harvested_source_execution_queue.csv"
    with out.open("w",encoding="utf-8",newline="") as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0].keys()))
        w.writeheader(); w.writerows(rows)


if __name__=="__main__":
    main()
