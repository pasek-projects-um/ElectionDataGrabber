from __future__ import annotations
from dataclasses import dataclass
from enum import Enum
from urllib.parse import urljoin, urlparse
import re

ELECTION_TERMS=("election","voting","vote","result","ballot","clerk","referendum","archive")

class SourceStatus(str, Enum):
    CANDIDATE="candidate"
    REACHABLE="reachable"
    REDIRECTED="redirected"
    VERIFIED_OFFICIAL="verified_official"
    ARTIFACT_FOUND="artifact_found"
    DEAD="dead"
    REPLACED="replaced"

@dataclass(frozen=True)
class SourceCandidate:
    locality: str
    url: str
    status: SourceStatus=SourceStatus.CANDIDATE
    discovered_from: str | None=None
    score: float=0.0

def election_link_score(url: str, text: str="") -> float:
    hay=(url+" "+text).lower()
    score=sum(1.0 for t in ELECTION_TERMS if t in hay)
    host=urlparse(url).hostname or ""
    if host.endswith(".gov") or ".gov." in host: score += 2
    return score

def discover_candidate_links(base_url: str, html: str) -> list[SourceCandidate]:
    links=re.findall(r'href=[\'"]([^\'"]+)[\'"]',html,re.I)
    out={}
    for href in links:
        url=urljoin(base_url,href)
        score=election_link_score(url)
        if score <= 0: continue
        if url not in out or score > out[url].score:
            out[url]=SourceCandidate("",url,SourceStatus.CANDIDATE,base_url,score)
    return sorted(out.values(),key=lambda x:(-x.score,x.url))
