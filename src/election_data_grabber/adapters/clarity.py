from __future__ import annotations

import re
from dataclasses import dataclass
from urllib.parse import urljoin

from bs4 import BeautifulSoup

@dataclass(frozen=True)
class ClaritySurface:
    election_root: str
    summary_url: str | None
    downloadable_urls: tuple[str,...]

def is_clarity(url: str, body: bytes | None=None) -> bool:
    blob=url.lower()+" "+((body or b"")[:200000].decode("utf-8",errors="ignore").lower())
    return "clarityelections.com" in blob or "election night reporting" in blob

def clarity_election_root(url: str) -> str:
    m=re.match(r'(https?://results\.enr\.clarityelections\.com/[^/]+/[^/]+/\d+/)',url,re.I)
    return m.group(1) if m else urljoin(url,"./")

def discover_clarity_downloads(body: bytes, base_url: str) -> ClaritySurface:
    soup=BeautifulSoup(body,"html.parser")
    downloads=set(); summary=None
    for a in soup.find_all("a",href=True):
        url=urljoin(base_url,str(a["href"]))
        label=" ".join(a.stripped_strings).lower()
        blob=(url+" "+label).lower()
        if any(x in blob for x in (".csv",".xml",".json",".zip","download","detail report","precinct")):
            downloads.add(url)
        if "summary" in blob and summary is None: summary=url
    return ClaritySurface(clarity_election_root(base_url),summary,tuple(sorted(downloads)))

def discover_clarity_urls(body: bytes) -> list[str]:
    text=body.decode("utf-8",errors="ignore")
    return sorted(set(re.findall(r'https://results\.enr\.clarityelections\.com/[^\s\'"<>]+',text,re.I)))
