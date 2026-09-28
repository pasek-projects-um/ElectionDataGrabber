from __future__ import annotations

import argparse
import csv
import urllib.error
import urllib.request
from pathlib import Path

from election_data_grabber.platform_fingerprint import fingerprint_result_surface

FIELDS=[
    "state","source_url","source_origin","fetch_status","http_status",
    "platform_family","confidence","evidence","discovered_artifacts",
]


def read_rows(path: Path) -> list[dict[str,str]]:
    with path.open(encoding="utf-8-sig",newline="") as f:
        return list(csv.DictReader(f))


def fetch_text(url: str, timeout: int) -> tuple[str|None,str,str]:
    req=urllib.request.Request(url,headers={"User-Agent":"ElectionDataGrabber/1.0 harvested-source-probe"})
    try:
        with urllib.request.urlopen(req,timeout=timeout) as resp:
            body=resp.read()
            return body.decode("utf-8",errors="replace"),"fetchable",str(getattr(resp,"status",200) or 200)
    except urllib.error.HTTPError as exc:
        return None,f"http_{exc.code}",str(exc.code)
    except urllib.error.URLError:
        return None,"network_error",""
    except TimeoutError:
        return None,"timeout",""


def probe(rows: list[dict[str,str]], *, timeout: int=10, limit: int|None=None) -> list[dict[str,str]]:
    if limit is not None:
        rows=rows[:limit]
    out=[]
    for row in rows:
        text,status,http_status=fetch_text(row["source_url"],timeout)
        if text is None:
            out.append({
                "state":row["state"],"source_url":row["source_url"],"source_origin":row["source_origin"],
                "fetch_status":status,"http_status":http_status,"platform_family":row.get("platform_family",""),
                "confidence":"","evidence":"","discovered_artifacts":"",
            })
            continue
        fp=fingerprint_result_surface(row["source_url"],text)
        out.append({
            "state":row["state"],"source_url":row["source_url"],"source_origin":row["source_origin"],
            "fetch_status":status,"http_status":http_status,"platform_family":fp.family,
            "confidence":fp.confidence,"evidence":"|".join(fp.evidence),
            "discovered_artifacts":"|".join(fp.discovered_artifacts),
        })
    return out


def write_rows(path: Path, rows: list[dict[str,str]]) -> None:
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open("w",encoding="utf-8",newline="") as f:
        w=csv.DictWriter(f,fieldnames=FIELDS)
        w.writeheader(); w.writerows(rows)


def main() -> None:
    p=argparse.ArgumentParser()
    p.add_argument("--input",type=Path,default=Path("audit/harvested_source_execution_queue.csv"))
    p.add_argument("--output",type=Path,default=Path("audit/harvested_source_probe.csv"))
    p.add_argument("--timeout",type=int,default=8)
    p.add_argument("--limit",type=int)
    args=p.parse_args()
    write_rows(args.output,probe(read_rows(args.input),timeout=args.timeout,limit=args.limit))


if __name__=="__main__":
    main()
