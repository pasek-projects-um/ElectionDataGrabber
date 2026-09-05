from __future__ import annotations

import json
import re
from datetime import datetime
from typing import Any

from bs4 import BeautifulSoup

from election_data_grabber.models import ResultObservation, VoteMode

_MODE_KEYS = {
    "electionday": VoteMode.ELECTION_DAY, "election_day": VoteMode.ELECTION_DAY,
    "early": VoteMode.EARLY, "earlyvoting": VoteMode.EARLY,
    "absentee": VoteMode.ABSENTEE, "av": VoteMode.ABSENTEE,
    "mail": VoteMode.MAIL, "provisional": VoteMode.PROVISIONAL,
    "votes": VoteMode.TOTAL, "total": VoteMode.TOTAL, "votecount": VoteMode.TOTAL,
}
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
                               source_id: str, fetched_at: datetime) -> list[ResultObservation]:
    """Normalize Enhanced Voting embedded result records when exposed in the page payload.

    The public shell can change independently of the result JSON. This parser therefore
    searches embedded JSON semantically and refuses to infer ballot order from display order.
    """
    out=[]
    seen=set()
    for doc in embedded_json_documents(body):
        for d in _walk(doc):
            unit=_first(d,_UNIT_KEYS); contest=_first(d,_CONTEST_KEYS); choice=_first(d,_CHOICE_KEYS)
            if not (unit and contest and choice): continue
            party=_first(d,_PARTY_KEYS)
            lower={str(k).lower():v for k,v in d.items()}
            for key,mode in _MODE_KEYS.items():
                if key not in lower: continue
                votes=_int(lower[key])
                if votes is None: continue
                sig=(str(unit),str(contest),str(choice),mode.value,votes)
                if sig in seen: continue
                seen.add(sig)
                out.append(ResultObservation(
                    election_id=election_id,jurisdiction_id=jurisdiction_id,
                    reporting_unit_id=f"{jurisdiction_id}:{unit}",reporting_unit_name=str(unit),
                    contest_name=str(contest),choice_name=str(choice),party=str(party) if party else None,
                    votes=votes,vote_mode=mode,source_id=source_id,fetched_at=fetched_at,
                    raw_vote_mode=key,
                ))
    return out
