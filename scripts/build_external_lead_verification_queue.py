from __future__ import annotations

import csv
from pathlib import Path
from urllib.parse import urlparse


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def build_verification_queue(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    out=[]
    for row in rows:
        url=row["lead_url"]
        host=(urlparse(url).hostname or "").lower()
        priority=0
        reasons=[]
        if row.get("verification_status")!="verified":
            priority += 2
            reasons.append("unverified")
        if row.get("official_status")=="likely_official":
            priority += 2
            reasons.append("likely_official")
        if url.startswith("http://"):
            priority += 1
            reasons.append("legacy_http")
        if "current-election" in url or "eid=" in url or "2020" in url:
            priority += 1
            reasons.append("cycle_or_current_pointer")
        out.append({
            **row,
            "host":host,
            "verification_priority":str(priority),
            "verification_reasons":";".join(reasons),
        })
    return sorted(out,key=lambda r:(-int(r["verification_priority"]),r["state"],r["lead_url"]))


def main() -> None:
    root=Path(__file__).resolve().parents[1]
    rows=read_rows(root/"audit/external_leads_electproject_2020.csv")
    queue=build_verification_queue(rows)
    out=root/"audit/external_lead_verification_queue.csv"
    with out.open("w",encoding="utf-8",newline="") as f:
        w=csv.DictWriter(f,fieldnames=list(queue[0].keys()))
        w.writeheader()
        w.writerows(queue)


if __name__=="__main__":
    main()
