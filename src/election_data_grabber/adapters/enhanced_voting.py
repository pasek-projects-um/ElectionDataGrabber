from __future__ import annotations

import json
import re
from datetime import datetime
from typing import Any

from bs4 import BeautifulSoup

from election_data_grabber.models import (
    ReportingProgress, ReportingProgressBasis, ReportingProgressKind,
    ResultObservation, UpdateSemantics, VoteMode,
)
from election_data_grabber.reporting_unit_identity import AdapterReportingContext, UnitType
from election_data_grabber.vote_modes import normalize_vote_mode

_MODE_KEYS = ("electionday","election_day","early","earlyvoting","absentee","av","mail","provisional","votes","total","votecount")
_UNIT_KEYS=("precinct","precinctName","reportingUnit","reportingUnitName","ward")
_CONTEST_KEYS=("contest","contestName","office","race","raceName")
_CHOICE_KEYS=("candidate","candidateName","choice","choiceName","option")
_PARTY_KEYS=("party","partyName","candidateParty")


def is_enhanced_voting(url: str, body: bytes | None = None) -> bool:
    blob=url.lower()+" "+((body or b"")[:200000].decode("utf-8",errors="ignore").lower())
    return "enhancedvoting.com" in blob or "enhanced voting" in blob


def discover_enhanced_voting_urls(body: bytes) -> list[str]:
    text=body.decode("utf-8",errors="ignore")
    return sorted(set(re.findall(r'https://app\.enhancedvoting\.com/results/public/[^\s\'"<>]+',text,re.I)))


def _first(d: dict[str,Any], keys) -> Any:
    lower={str(k).lower():v for k,v in d.items()}
    for key in keys:
        if key in d and d[key] not in (None,""): return d[key]
        if key.lower() in lower and lower[key.lower()] not in (None,""): return lower[key.lower()]
    return None


def _int(v: Any) -> int | None:
    if v is None: return None
    try: return int(str(v).replace(",","").strip())
    except (ValueError,TypeError): return None


def _state_from_jurisdiction(jurisdiction_id: str) -> str | None:
    parts=jurisdiction_id.lower().split(":")
    if len(parts)>=2 and parts[0]=="us" and len(parts[1])==2: return parts[1].upper()
    for state in ("mi","oh","pa","me"):
        if jurisdiction_id.lower().startswith(state+"-"): return state.upper()
    return None


def embedded_json_documents(body: bytes) -> list[Any]:
    soup=BeautifulSoup(body,"html.parser")
    docs=[]
    for script in soup.find_all("script"):
        typ=(script.get("type") or "").lower()
        text=script.string or script.get_text("",strip=False)
        if not text: continue
        if typ=="application/json" or script.get("id")=="__NEXT_DATA__":
            try: docs.append(json.loads(text))
            except json.JSONDecodeError: pass
        for m in re.finditer(r'(?:window\.__\w+|__INITIAL_STATE__)\s*=\s*(\{.*?\});?\s*(?:</script>|$)',text,re.S):
            try: docs.append(json.loads(m.group(1)))
            except json.JSONDecodeError: pass
    return docs


def _walk(obj: Any):
    if isinstance(obj,dict):
        yield obj
        for v in obj.values(): yield from _walk(v)
    elif isinstance(obj,list):
        for v in obj: yield from _walk(v)


def parse_enhanced_voting_html(body: bytes, *, election_id: str, jurisdiction_id: str,
                               source_id: str, fetched_at: datetime,
                               reporting_context: AdapterReportingContext | None = None) -> list[ResultObservation]:
    if reporting_context is not None:
        reporting_context.validate_call(election_id=election_id, source_id=source_id)
    out=[]
    seen=set()
    state=_state_from_jurisdiction(reporting_context.jurisdiction_id if reporting_context else jurisdiction_id)
    for doc in embedded_json_documents(body):
        for d in _walk(doc):
            unit=_first(d,_UNIT_KEYS); contest=_first(d,_CONTEST_KEYS); choice=_first(d,_CHOICE_KEYS)
            if not (unit and contest and choice): continue
            party=_first(d,_PARTY_KEYS)
            lower={str(k).lower():v for k,v in d.items()}
            for key in _MODE_KEYS:
                if key not in lower: continue
                votes=_int(lower[key])
                if votes is None: continue
                resolution=normalize_vote_mode(key,state=state,source_id=source_id)
                mode=resolution.vote_mode or VoteMode.UNKNOWN
                sig=(str(unit),str(contest),str(choice),key,votes)
                if sig in seen: continue
                seen.add(sig)
                out.append(ResultObservation(
                    election_id=election_id,jurisdiction_id=(reporting_context.jurisdiction_id if reporting_context else jurisdiction_id),
                    reporting_unit_id=(reporting_context.unit_id(UnitType.PRECINCT, str(unit), str(unit)) if reporting_context else f"{jurisdiction_id}:{unit}"),reporting_unit_name=str(unit),
                    reporting_regime_id=(reporting_context.regime_id if reporting_context else None),
                    reporting_unit_raw_name=(str(unit) if reporting_context else None),reporting_unit_source_native_id=(str(unit) if reporting_context else None),
                    snapshot_sha256=(reporting_context.snapshot_sha256 if reporting_context else None),
                    contest_name=str(contest),choice_name=str(choice),party=str(party) if party else None,
                    votes=votes,vote_mode=mode,source_id=source_id,fetched_at=fetched_at,
                    raw_vote_mode=key,
                    vote_mode_mapping_method=(resolution.rule.mapping_method if resolution.rule else None),
                    vote_mode_evidence_reference=(resolution.rule.evidence_reference if resolution.rule else None),
                ))
    return out


_PROGRESS_REPORTING_KEYS=("precinctsReporting","reportingPrecincts","precincts_reported","reporting")
_PROGRESS_TOTAL_KEYS=("precinctsTotal","totalPrecincts","precincts_total","expectedPrecincts")
_PROGRESS_COMPLETE_KEYS=("complete","isComplete","reportingComplete","resultsComplete")
_PROGRESS_SEMANTIC_KEYS=("incremental","isIncremental","cumulative","isCumulative")


def parse_enhanced_voting_progress(body: bytes, *, election_id: str, jurisdiction_id: str,
                                   source_id: str, fetched_at: datetime,
                                   reporting_context: AdapterReportingContext | None = None) -> list[ReportingProgress]:
    if reporting_context is not None:
        reporting_context.validate_call(election_id=election_id, source_id=source_id)
    out=[]
    seen=set()
    canonical_jurisdiction=reporting_context.jurisdiction_id if reporting_context else jurisdiction_id
    for doc in embedded_json_documents(body):
        for d in _walk(doc):
            reporting=_int(_first(d,_PROGRESS_REPORTING_KEYS))
            expected=_int(_first(d,_PROGRESS_TOTAL_KEYS))
            complete_raw=_first(d,_PROGRESS_COMPLETE_KEYS)
            semantic_raw=_first(d,_PROGRESS_SEMANTIC_KEYS)
            if reporting is None and expected is None and complete_raw is None:
                continue
            unit=_first(d,_UNIT_KEYS)
            scope="reporting_unit" if unit else "source"
            unit_id=None
            unit_name=str(unit) if unit else None
            if unit and reporting_context is not None:
                unit_id=reporting_context.unit_id(UnitType.PRECINCT,str(unit),str(unit))
            elif unit:
                unit_id=f"{jurisdiction_id}:{unit}"
            semantics=UpdateSemantics.UNKNOWN
            raw_semantic=str(semantic_raw).strip().lower() if semantic_raw is not None else ""
            if "increment" in raw_semantic or raw_semantic in {"true","1"} and any(k.lower().startswith("increment") for k in map(str,d.keys())):
                semantics=UpdateSemantics.INCREMENTAL
            elif "cumul" in raw_semantic:
                semantics=UpdateSemantics.CUMULATIVE
            complete=None
            if isinstance(complete_raw,bool):
                complete=complete_raw
            elif complete_raw is not None:
                raw=str(complete_raw).strip().lower()
                if raw in {"true","yes","1","complete","completed","final"}: complete=True
                elif raw in {"false","no","0","incomplete","partial"}: complete=False
            raw_status=json.dumps(
                {str(k): d[k] for k in d if str(k) in set(_PROGRESS_REPORTING_KEYS+_PROGRESS_TOTAL_KEYS+_PROGRESS_COMPLETE_KEYS+_PROGRESS_SEMANTIC_KEYS)},
                sort_keys=True,
                default=str,
            )
            sig=(scope,unit_id,reporting,expected,complete,semantics.value,raw_status)
            if sig in seen: continue
            seen.add(sig)
            if reporting is not None or expected is not None:
                out.append(ReportingProgress(
                    election_id=election_id,jurisdiction_id=canonical_jurisdiction,source_id=source_id,
                    fetched_at=fetched_at,reporting_regime_id=(reporting_context.regime_id if reporting_context else None),
                    reporting_unit_id=unit_id,reporting_unit_name=unit_name,scope=scope,
                    kind=ReportingProgressKind.SOURCE_COUNTS,basis=ReportingProgressBasis.SOURCE_REPORTED,
                    update_semantics=semantics,reporting_count=reporting,expected_count=expected,
                    snapshot_sha256=(reporting_context.snapshot_sha256 if reporting_context else None),
                    raw_status=raw_status,
                ))
            if complete is not None:
                out.append(ReportingProgress(
                    election_id=election_id,jurisdiction_id=canonical_jurisdiction,source_id=source_id,
                    fetched_at=fetched_at,reporting_regime_id=(reporting_context.regime_id if reporting_context else None),
                    reporting_unit_id=unit_id,reporting_unit_name=unit_name,scope=scope,
                    kind=ReportingProgressKind.SOURCE_COMPLETE,basis=ReportingProgressBasis.SOURCE_REPORTED,
                    update_semantics=semantics,complete=complete,
                    snapshot_sha256=(reporting_context.snapshot_sha256 if reporting_context else None),
                    raw_status=raw_status,
                ))
    return out
