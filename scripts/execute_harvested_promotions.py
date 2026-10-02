from __future__ import annotations

import argparse
import csv
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

from election_data_grabber.adapters.clarity import discover_clarity_downloads, select_clarity_detail_artifact
from election_data_grabber.adapters.vendor_structured import discover_vendor_artifacts
from election_data_grabber.adapters.structured_web import select_structured_artifact, sniff_payload_kind
from election_data_grabber.execution_maturity import maturity_row
from election_data_grabber.supported_execution import execute_supported_body
import urllib.error
import urllib.request
import zipfile
import xml.etree.ElementTree as ET



FIELDS=[
    "state","result_url","access_family","parser","execution_stage","observation_count",
    "smallest_observed_unit","vote_modes_preserved","failure_class","snapshot_sha256",
]


def fetch_body(url: str, timeout: int) -> tuple[bytes | None, str]:
    req=urllib.request.Request(url,headers={"User-Agent":"ElectionDataGrabber/1.0 harvested-execution-depth"})
    try:
        with urllib.request.urlopen(req,timeout=timeout) as resp:
            return resp.read(),""
    except urllib.error.HTTPError as exc:
        return None,f"http_{exc.code}"
    except urllib.error.URLError:
        return None,"network_error"
    except TimeoutError:
        return None,"timeout"


def failed_row(row: dict[str,str], failure_class: str) -> dict[str,str]:
    return {
        "state":row.get("state",""),
        "result_url":row.get("result_url",""),
        "access_family":row.get("access_family",""),
        "parser":row.get("parser",""),
        "execution_stage":"discovered",
        "observation_count":"0",
        "smallest_observed_unit":row.get("smallest_observed_unit","unknown"),
        "vote_modes_preserved":"",
        "failure_class":failure_class,
        "snapshot_sha256":"",
    }


def read_rows(path: Path) -> list[dict[str,str]]:
    with path.open(encoding="utf-8-sig",newline="") as f:
        return list(csv.DictReader(f))


def parser_for_payload_kind(kind: str) -> tuple[str,str]:
    if kind=="json":
        return "structured_json","election_data_grabber.adapters.generic_json:parse_generic_results_json"
    if kind=="csv":
        return "tabular_download","election_data_grabber.adapters.generic_csv:parse_generic_precinct_csv"
    if kind=="excel":
        return "tabular_download","election_data_grabber.adapters.generic_excel:parse_generic_precinct_excel"
    return "",""


def parser_for_artifact(url: str) -> tuple[str,str]:
    path=urlparse(url).path.lower()
    if path.endswith(".json") or "/api/" in path:
        return "structured_json","election_data_grabber.adapters.generic_json:parse_generic_results_json"
    if path.endswith(".csv"):
        return "tabular_download","election_data_grabber.adapters.generic_csv:parse_generic_precinct_csv"
    if path.endswith((".xlsx",".xls")):
        return "tabular_download","election_data_grabber.adapters.generic_excel:parse_generic_precinct_excel"
    if path.endswith(".xml"):
        return "structured_xml","election_data_grabber.adapters.clarity_xml:parse_clarity_like_xml"
    return "",""


def discover_structured_from_markup(body: bytes, base_url: str) -> str|None:
    selected=select_structured_artifact(discover_vendor_artifacts(body,base_url))
    return selected.url if selected else None


def discover_artifact(row: dict[str,str], body: bytes) -> str|None:
    route=row.get("execution_route","")
    url=row["source_url"]
    if route=="election_data_grabber.adapters.clarity:discover_clarity_downloads":
        return select_clarity_detail_artifact(discover_clarity_downloads(body,url))
    if route=="election_data_grabber.adapters.vendor_structured:discover_vendor_artifacts":
        selected=select_structured_artifact(discover_vendor_artifacts(body,url))
        return selected.url if selected else None
    return None


def execute_promotions(rows: list[dict[str,str]], *, timeout: int=12, limit: int|None=None) -> list[dict[str,str]]:
    if limit is not None:
        rows=rows[:limit]
    out=[]
    fetched_at=datetime.now(timezone.utc)
    for index,row in enumerate(rows,start=1):
        action=row.get("promotion_action","")
        if action=="fetch_blocked":
            out.append(failed_row({
                "state":row.get("state",""),
                "result_url":row.get("source_url",""),
                "access_family":row.get("promoted_family",""),
                "parser":row.get("execution_route",""),
                "smallest_observed_unit":"unknown",
            },"promotion_fetch_blocked"))
            continue

        target_url=row.get("source_url","")
        family=row.get("promoted_family","")
        parser=row.get("execution_route","")

        if action=="discover_artifact":
            landing,failure=fetch_body(target_url,timeout)
            if landing is None:
                out.append(failed_row({
                    "state":row.get("state",""),
                    "result_url":target_url,
                    "access_family":family,
                    "parser":parser,
                    "smallest_observed_unit":"unknown",
                },failure))
                continue
            artifact=discover_artifact(row,landing)
            if not artifact:
                out.append(failed_row({
                    "state":row.get("state",""),
                    "result_url":target_url,
                    "access_family":family,
                    "parser":parser,
                    "smallest_observed_unit":"unknown",
                },"no_structured_artifact_discovered"))
                continue
            target_url=artifact
            family,parser=parser_for_artifact(artifact)
            if not parser:
                out.append(failed_row({
                    "state":row.get("state",""),
                    "result_url":artifact,
                    "access_family":family,
                    "parser":"",
                    "smallest_observed_unit":"unknown",
                },"artifact_family_not_executable"))
                continue

        if action not in {"execute_now","discover_artifact"}:
            out.append(failed_row({
                "state":row.get("state",""),
                "result_url":target_url,
                "access_family":family,
                "parser":parser,
                "smallest_observed_unit":"unknown",
            },"needs_platform_work"))
            continue

        body,failure=fetch_body(target_url,timeout)
        if body is None:
            out.append(failed_row({
                "state":row.get("state",""),
                "result_url":target_url,
                "access_family":family,
                "parser":parser,
                "smallest_observed_unit":"unknown",
            },failure))
            continue

        payload_kind=sniff_payload_kind(body)
        expected_kind=(
            "json" if parser.endswith("parse_generic_results_json") else
            "csv" if parser.endswith("parse_generic_precinct_csv") else
            "excel" if parser.endswith("parse_generic_precinct_excel") else
            "xml" if parser.endswith("parse_clarity_like_xml") else
            ""
        )
        if expected_kind and payload_kind not in {expected_kind,"unknown"}:
            payload_family,payload_parser=parser_for_payload_kind(payload_kind)
            if payload_parser:
                family,parser=payload_family,payload_parser
                expected_kind=payload_kind
            elif payload_kind=="xml" and body.lstrip().lower().startswith((b"<html",b"<!doctype html")):
                artifact=discover_structured_from_markup(body,target_url)
                if not artifact:
                    out.append(failed_row({
                        "state":row.get("state",""),
                        "result_url":target_url,
                        "access_family":family,
                        "parser":parser,
                        "smallest_observed_unit":"unknown",
                    },"landing_page_no_structured_artifact"))
                    continue
                artifact_body,artifact_failure=fetch_body(artifact,timeout)
                if artifact_body is None:
                    out.append(failed_row({
                        "state":row.get("state",""),
                        "result_url":artifact,
                        "access_family":family,
                        "parser":parser,
                        "smallest_observed_unit":"unknown",
                    },artifact_failure))
                    continue
                target_url=artifact
                body=artifact_body
                family,parser=parser_for_artifact(artifact)
                if not parser:
                    artifact_kind=sniff_payload_kind(body)
                    family,parser=parser_for_payload_kind(artifact_kind)
                if not parser:
                    out.append(failed_row({
                        "state":row.get("state",""),
                        "result_url":artifact,
                        "access_family":family,
                        "parser":"",
                        "smallest_observed_unit":"unknown",
                    },"artifact_family_not_executable"))
                    continue
                payload_kind=sniff_payload_kind(body)
                expected_kind=(
                    "json" if parser.endswith("parse_generic_results_json") else
                    "csv" if parser.endswith("parse_generic_precinct_csv") else
                    "excel" if parser.endswith("parse_generic_precinct_excel") else
                    "xml" if parser.endswith("parse_clarity_like_xml") else
                    ""
                )
            else:
                out.append(failed_row({
                    "state":row.get("state",""),
                    "result_url":target_url,
                    "access_family":family,
                    "parser":parser,
                    "smallest_observed_unit":"unknown",
                },f"payload_format_mismatch:{expected_kind}:{payload_kind}"))
                continue

        manifest={
            "state":row.get("state",""),
            "result_url":target_url,
            "access_family":family,
            "parser":parser,
            "smallest_observed_unit":"unknown",
        }
        if parser.endswith("parse_generic_precinct_excel") and not urlparse(target_url).path.lower().endswith((".xlsx",".xls")):
            hint=(row.get("discovered_artifacts","")+" "+row.get("evidence","")).lower()
            if ".xlsx" in hint:
                manifest["result_url"]=target_url+".xlsx"
            elif ".xls" in hint:
                manifest["result_url"]=target_url+".xls"
            else:
                out.append(failed_row({
                    "state":row.get("state",""),
                    "result_url":target_url,
                    "access_family":family,
                    "parser":parser,
                    "smallest_observed_unit":"unknown",
                },"excel_format_ambiguous"))
                continue

        try:
            evidence=execute_supported_body(
                manifest,
                body,
                election_id="harvested-execution-depth",
                jurisdiction_id=f"us:{row.get('state','').lower()}:harvested-{index}",
                source_id=f"harvested-depth:{index}",
                fetched_at=fetched_at,
            )
        except (ValueError, TypeError, KeyError, UnicodeError, OSError, zipfile.BadZipFile, ET.ParseError) as exc:
            out.append(failed_row({
                "state":row.get("state",""),
                "result_url":manifest.get("result_url",target_url),
                "access_family":family,
                "parser":parser,
                "smallest_observed_unit":"unknown",
            },f"parser_exception:{type(exc).__name__}"))
            continue
        out.append(maturity_row(evidence))
    return out


def main() -> None:
    p=argparse.ArgumentParser()
    p.add_argument("--input",type=Path,default=Path("audit/harvested_source_execution_promotions.csv"))
    p.add_argument("--output",type=Path,default=Path("audit/harvested_source_execution_results.csv"))
    p.add_argument("--timeout",type=int,default=12)
    p.add_argument("--limit",type=int)
    args=p.parse_args()
    rows=execute_promotions(read_rows(args.input),timeout=args.timeout,limit=args.limit)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    with args.output.open("w",encoding="utf-8",newline="") as f:
        w=csv.DictWriter(f,fieldnames=FIELDS); w.writeheader(); w.writerows(rows)


if __name__=="__main__":
    main()
