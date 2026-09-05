from __future__ import annotations

from dataclasses import dataclass
import re
from urllib.parse import urljoin

from bs4 import BeautifulSoup


ELECTION_DOC_RE = re.compile(
    r"(election|results?|statement of votes|canvass|precinct|ward|turnout|referendum|ballot)",
    re.I,
)


@dataclass(frozen=True, slots=True)
class ArchiveArtifact:
    url: str
    label: str
    kind: str


def classify_artifact(url: str, label: str) -> str:
    blob = f"{url} {label}".lower()
    if ".pdf" in blob:
        return "pdf"
    if any(ext in blob for ext in (".xlsx", ".xls")):
        return "spreadsheet"
    if ".csv" in blob:
        return "csv"
    if "results" in blob or "election" in blob:
        return "web"
    return "other"


def discover_election_artifacts(body: bytes, base_url: str) -> list[ArchiveArtifact]:
    """Discover likely election-result artifacts from municipal/state archive pages.

    This intentionally uses semantic labels/extensions rather than locality-specific
    selectors so the same helper can be reused across Maine and later states.
    """
    soup = BeautifulSoup(body, "html.parser")
    found: dict[str, ArchiveArtifact] = {}
    for a in soup.find_all("a", href=True):
        label = " ".join(a.stripped_strings)
        href = urljoin(base_url, str(a["href"]))
        if not ELECTION_DOC_RE.search(f"{label} {href}"):
            continue
        found[href] = ArchiveArtifact(href, label, classify_artifact(href, label))
    return sorted(found.values(), key=lambda x: x.url)
