from __future__ import annotations

from dataclasses import dataclass
import re
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup


RESULT_RE = re.compile(
    r"(election\s+results?|official\s+results?|statement\s+of\s+votes?|canvass|"
    r"precinct\s+results?|ward\s+results?|turnout|referendum\s+results?)",
    re.I,
)
ELECTION_CONTEXT_RE = re.compile(r"(election|primary|general|referendum|vote|ballot)", re.I)
NEGATIVE_RE = re.compile(
    r"(absentee\s+(ballot\s+)?(request|application)|request\s+absentee|"
    r"voter\s+registration|faq|frequently\s+asked|search\s+results?|"
    r"sample\s+ballot|polling\s+place|where\s+do\s+i\s+vote)",
    re.I,
)
DYNAMIC_DOC_RE = re.compile(r"(tyler|portico|navigator|documentcenter|laserfiche)", re.I)


@dataclass(frozen=True, slots=True)
class ArchiveArtifact:
    url: str
    label: str
    kind: str


def classify_artifact(url: str, label: str) -> str:
    blob = f"{url} {label}".lower()
    if DYNAMIC_DOC_RE.search(blob):
        return "dynamic_document"
    if ".pdf" in blob:
        return "pdf"
    if any(ext in blob for ext in (".xlsx", ".xls")):
        return "spreadsheet"
    if ".csv" in blob:
        return "csv"
    if RESULT_RE.search(blob):
        return "web"
    return "other"


def looks_like_result_artifact(url: str, label: str) -> bool:
    blob = f"{url} {label}"
    if NEGATIVE_RE.search(blob) and not RESULT_RE.search(blob):
        return False
    kind = classify_artifact(url, label)
    if kind in {"pdf", "spreadsheet", "csv", "dynamic_document"}:
        # A document is only a result candidate when its label/path also carries
        # result/election context; this prevents absentee applications and FAQs
        # from entering the parser portability audit.
        return bool(RESULT_RE.search(blob) or (ELECTION_CONTEXT_RE.search(blob) and "result" in blob.lower()))
    return bool(RESULT_RE.search(blob))


def discover_election_artifacts(body: bytes, base_url: str) -> list[ArchiveArtifact]:
    """Discover likely election-result artifacts without promoting election-adjacent material."""
    soup = BeautifulSoup(body, "html.parser")
    found: dict[str, ArchiveArtifact] = {}
    for a in soup.find_all("a", href=True):
        label = " ".join(a.stripped_strings)
        href = urljoin(base_url, str(a["href"]))
        if not looks_like_result_artifact(href, label):
            continue
        found[href] = ArchiveArtifact(href, label, classify_artifact(href, label))
    return sorted(found.values(), key=lambda x: x.url)
