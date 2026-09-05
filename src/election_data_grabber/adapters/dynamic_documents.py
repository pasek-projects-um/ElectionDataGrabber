from __future__ import annotations
from dataclasses import dataclass
import re
from urllib.parse import urljoin

from bs4 import BeautifulSoup

PLATFORM_PATTERNS = {
    "tyler_portico": re.compile(r"(tyler|portico|navigator)", re.I),
    "document_center": re.compile(r"(documentcenter|document-center)", re.I),
    "laserfiche": re.compile(r"laserfiche", re.I),
}

@dataclass(frozen=True)
class DynamicDocumentCandidate:
    platform: str
    url: str
    label: str

def fingerprint_dynamic_document(url: str, body: bytes | None = None) -> str | None:
    text=url
    if body:
        text += " " + body.decode("utf-8", errors="ignore")[:100000]
    for name,pattern in PLATFORM_PATTERNS.items():
        if pattern.search(text):
            return name
    return None

def discover_dynamic_documents(body: bytes, base_url: str) -> list[DynamicDocumentCandidate]:
    soup=BeautifulSoup(body,"html.parser")
    out=[]
    for a in soup.find_all("a",href=True):
        url=urljoin(base_url,str(a["href"]))
        label=" ".join(a.stripped_strings)
        platform=fingerprint_dynamic_document(url)
        if platform and re.search(r"(election|result|vote|canvass|primary|general)",label+" "+url,re.I):
            out.append(DynamicDocumentCandidate(platform,url,label))
    return out
