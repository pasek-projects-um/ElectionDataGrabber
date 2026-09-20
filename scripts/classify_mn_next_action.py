from __future__ import annotations

import csv
from pathlib import Path

TARGET_STATES={"MN"}


def classify_rows(expansion_path: Path) -> list[dict[str,str]]:
    rows=list(csv.DictReader(expansion_path.open(encoding="utf-8")))
    out=[]
    for r in rows:
        if r["state"] not in TARGET_STATES:
            continue
        status=r.get("status","")
        result_links=(r.get("result_links") or "").strip()
        if status=="reached" and result_links:
            action="promote_result_source"
        elif status=="reached":
            action="inspect_reached_authority"
        else:
            action="resolve_directory"
        out.append({
            "state":r["state"],
            "authority_url":(r.get("authority_url") or "").strip(),
            "authority_host":(r.get("authority_host") or "").strip().lower(),
            "result_links":result_links,
            "election_night_candidate":r.get("election_night_candidate",""),
            "smallest_observed_unit":r.get("smallest_observed_unit",""),
            "platform_family":r.get("platform_family",""),
            "status":status,
            "next_action":action,
        })
    return out


def write(rows: list[dict[str,str]], path: Path) -> None:
    path.parent.mkdir(parents=True,exist_ok=True)
    fields=list(rows[0]) if rows else [
        "state","authority_url","authority_host","result_links","election_night_candidate",
        "smallest_observed_unit","platform_family","status","next_action",
    ]
    with path.open("w",newline="",encoding="utf-8") as f:
        w=csv.DictWriter(f,fieldnames=fields); w.writeheader(); w.writerows(rows)


if __name__=="__main__":
    root=Path(__file__).resolve().parents[1]
    write(classify_rows(root/"audit/us-state-central-authority-expansion.csv"),root/"audit/mn_next_action.csv")
