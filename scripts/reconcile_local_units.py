from __future__ import annotations

import argparse
import csv
import re
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse

from election_data_grabber.canonical_ids import authority_id, jurisdiction_id

GENERIC = {
    "elections","election","voting","vote","results","result","auditor","auditors",
    "clerk","clerks","county","counties","official","officials","sos","state",
    "www","gov","government","departments","department","about","contact",
}
COUNTY_PATTERNS = [
    re.compile(r"(?:www\.)?([a-z][a-z0-9-]*?)county", re.I),
    re.compile(r"county[-_/]([a-z][a-z0-9-]+)", re.I),
]
STATE_LEVEL = {"county","county_equivalent","parish","municipality","town","election_authority"}


@dataclass(frozen=True)
class Candidate:
    state: str
    name_token: str
    jurisdiction_level: str
    authority_url: str
    confidence: str
    method: str


def infer(row: dict[str, str], model: str) -> Candidate | None:
    url = row.get("authority_url", "")
    if row.get("status") != "reached" or not url:
        return None
    host = (urlparse(url).hostname or "").lower()
    path = urlparse(url).path.lower()
    token = ""
    for pat in COUNTY_PATTERNS:
        m = pat.search(host + path)
        if m:
            token = m.group(1); break
    if not token:
        labels = [x for x in re.split(r"[^a-z0-9]+", host + " " + path) if len(x) > 2]
        useful = [x for x in labels if x not in GENERIC and not x.isdigit()]
        # Host/path heuristics without an explicit county marker are evidence,
        # but not strong enough for automatic canonical reconciliation.
        return None
    token = token.strip("-")
    if not token or token in GENERIC:
        return None
    if "parish" in model:
        level = "parish"
    elif "municipal" in model or "town" in model:
        level = "municipality"
    elif "local-election-authority" in model:
        level = "election_authority"
    else:
        level = "county"
    return Candidate(row["state"], token, level, url, "high", "county_url_pattern")


def main() -> None:
    ap=argparse.ArgumentParser()
    ap.add_argument("--observations", type=Path, default=Path("audit/us-state-central-authority-expansion.csv"))
    ap.add_argument("--out", type=Path, default=Path("audit/us-local-unit-reconciliation.csv"))
    ap.add_argument("--tracker", type=Path, default=Path("registry/us_local_unit_coverage_tracker.csv"))
    args=ap.parse_args()

    with args.tracker.open(encoding="utf-8-sig") as f:
        tracker=list(csv.DictReader(f))
    models={r["state"]:r["authority_model"] for r in tracker}
    expected={r["state"]:int(r["expected_primary_units"]) for r in tracker}

    with args.observations.open(encoding="utf-8-sig") as f:
        observations=list(csv.DictReader(f))

    reconciled={}
    for row in observations:
        c=infer(row, models.get(row["state"], ""))
        if not c:
            continue
        jid=jurisdiction_id(c.state,c.jurisdiction_level,c.name_token)
        reconciled.setdefault(jid,c)

    # A heuristic can never enumerate more primary authorities than the state's
    # planning denominator. Overflow is a signal for manual/state-profile review.
    by_state={}
    for jid,c in sorted(reconciled.items()):
        by_state.setdefault(c.state,[]).append((jid,c))

    output=[]
    accepted_by_state={}
    for state, items in by_state.items():
        cap=expected.get(state,0)
        accepted=items[:cap]
        accepted_by_state[state]=len(accepted)
        for jid,c in accepted:
            output.append({
                "jurisdiction_id":jid,
                "authority_id":authority_id(jid,"election"),
                "state":state,
                "jurisdiction_level":c.jurisdiction_level,
                "canonical_name":c.name_token.replace("-"," ").title(),
                "id_status":"provisional_name",
                "authority_url":c.authority_url,
                "reconciliation_confidence":c.confidence,
                "reconciliation_method":c.method,
                "capability_status":"enumerated_unresolved",
            })

    args.out.parent.mkdir(parents=True,exist_ok=True)
    fields=["jurisdiction_id","authority_id","state","jurisdiction_level","canonical_name","id_status","authority_url","reconciliation_confidence","reconciliation_method","capability_status"]
    with args.out.open("w",newline="",encoding="utf-8") as f:
        w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(output)

    for row in tracker:
        n=accepted_by_state.get(row["state"],0)
        row["enumerated_unresolved"]=str(n)
        # Do not disturb adjudicated capability buckets.
        accounted=n+sum(int(row[k]) for k in ("known_final_only","known_election_night_only","known_both","known_units_missing_source"))
        row["estimated_unknown_units"]=str(max(0,int(row["expected_primary_units"])-accounted))
        row["status"]="partially_enumerated" if n else row["status"]

    with args.tracker.open("w",newline="",encoding="utf-8") as f:
        w=csv.DictWriter(f,fieldnames=list(tracker[0]));w.writeheader();w.writerows(tracker)

    print("RECONCILED",len(output),"jurisdictions",dict(sorted(accepted_by_state.items())))


if __name__=="__main__":
    main()
