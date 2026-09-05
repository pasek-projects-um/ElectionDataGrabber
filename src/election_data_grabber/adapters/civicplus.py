from __future__ import annotations

import re
from dataclasses import dataclass
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from election_data_grabber.adapters.clarity import is_clarity
from election_data_grabber.adapters.enhanced_voting import is_enhanced_voting

@dataclass(frozen=True)
class CivicPlusResultLink:
    url: str
    label: str
    downstream_family: str

def is_civicplus(url: str, body: bytes | None=None) -> bool:
    blob=url.lower()+" "+((body or b"")[:200000].decode("utf-8",errors="ignore").lower())
    return any(x in blob for x in ("civicplus","civicengage","documentcenter/view"))

def discover_civicplus_result_links(body: bytes, base_url: str) -> list[CivicPlusResultLink]:
    """Treat CivicPlus as an authority/discovery CMS and delegate to result vendors/files."""
    soup=BeautifulSoup(body,"html.parser")
    out={}
    for a in soup.find_all("a",href=True):
        label=" ".join(a.stripped_strings)
        url=urljoin(base_url,str(a["href"]))
        blob=(label+" "+url).lower()
        if not re.search(r"(election|unofficial|official|results?|statement of votes|canvass)",blob):
            continue
        if is_enhanced_voting(url): family="enhanced_voting"
        elif is_clarity(url): family="clarity"
        elif ".pdf" in url.lower() or "documentcenter/view" in url.lower(): family="document"
        elif any(x in url.lower() for x in (".csv",".xlsx",".xls")): family="structured_download"
        else: family="web"
        out[url]=CivicPlusResultLink(url,label,family)
    return sorted(out.values(),key=lambda x:(x.downstream_family,x.url))
