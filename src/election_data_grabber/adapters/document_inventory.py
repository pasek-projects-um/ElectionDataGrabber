from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urljoin

from bs4 import BeautifulSoup


@dataclass(frozen=True, slots=True)
class DocumentLink:
    url: str
    label: str
    format: str
    precinct_hint: bool
    summary_hint: bool
    audit_hint: bool


def inventory_document_links(body: bytes, base_url: str) -> list[DocumentLink]:
    """Inventory PDF/CSV/XLS/XLSX result artifacts from county archive pages."""
    soup = BeautifulSoup(body, "html.parser")
    found: dict[str, DocumentLink] = {}
    for a in soup.find_all("a", href=True):
        href = str(a["href"])
        lower = href.lower().split("?", 1)[0]
        ext = next((x for x in ("pdf", "csv", "xlsx", "xls") if lower.endswith("." + x)), None)
        if not ext:
            continue
        label = " ".join(a.stripped_strings).strip()
        blob = f"{label} {href}".lower()
        url = urljoin(base_url, href)
        found[url] = DocumentLink(
            url=url,
            label=label,
            format=ext,
            precinct_hint="precinct" in blob,
            summary_hint="summary" in blob or "cumulative" in blob,
            audit_hint="audit" in blob or "recount" in blob,
        )
    return sorted(found.values(), key=lambda x: x.url)
