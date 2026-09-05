from __future__ import annotations
import csv,json
from collections import Counter
from pathlib import Path

def main():
    files=sorted(Path("audit").glob("me-end-to-end-*.csv"))
    rows=[]
    for p in files:
        with p.open(encoding="utf-8") as f: rows.extend(csv.DictReader(f))
    pending=[r for r in rows if r.get("portability")=="pending"]
    buckets=Counter()
    for r in pending:
        status=(r.get("authority_status") or "").lower()
        url=(r.get("authority_url") or "").lower()
        if "fetch" in status or "failed" in status: bucket="authority_fetch_failed"
        elif not url: bucket="authority_unresolved"
        elif not r.get("artifact_url"): bucket="authority_resolved_no_result_artifact"
        else: bucket="artifact_needs_followup"
        buckets[bucket]+=1
    Path("audit/me-pending-buckets.json").write_text(json.dumps(dict(buckets),indent=2,sort_keys=True))
    print("PENDING_BUCKETS",json.dumps(dict(buckets),sort_keys=True))
if __name__=="__main__": main()
