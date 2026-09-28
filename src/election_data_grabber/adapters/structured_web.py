from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urlparse


@dataclass(frozen=True, slots=True)
class StructuredArtifact:
    url: str
    kind: str
    score: int


def artifact_kind(url: str) -> str:
    path=urlparse(url).path.lower()
    if path.endswith(".json") or "/api/" in path:
        return "json"
    if path.endswith(".xml"):
        return "xml"
    if path.endswith(".csv"):
        return "csv"
    if path.endswith((".xlsx",".xls")):
        return "excel"
    if path.endswith(".zip"):
        return "archive"
    return "unknown"


def rank_structured_artifacts(urls: list[str] | tuple[str,...]) -> list[StructuredArtifact]:
    ranked=[]
    for url in dict.fromkeys(urls):
        kind=artifact_kind(url)
        score={"json":50,"xml":40,"csv":30,"excel":20,"archive":10,"unknown":0}[kind]
        lower=url.lower()
        if "result" in lower:
            score += 5
        if "precinct" in lower or "detail" in lower:
            score += 4
        ranked.append(StructuredArtifact(url=url,kind=kind,score=score))
    return sorted(ranked,key=lambda x:(-x.score,x.url))


def select_structured_artifact(urls: list[str] | tuple[str,...]) -> StructuredArtifact | None:
    ranked=rank_structured_artifacts(urls)
    return ranked[0] if ranked and ranked[0].score>0 else None
