from __future__ import annotations

import re
from urllib.parse import urljoin


def discover_vendor_artifacts(body: bytes, base_url: str) -> tuple[str,...]:
    text=body.decode("utf-8",errors="ignore")
    urls=set()
    for match in re.findall(r'''(?:href|src)\s*=\s*["']([^"']+)["']''',text,flags=re.I):
        absolute=urljoin(base_url,match)
        lower=absolute.lower()
        if any(token in lower for token in (".json",".xml",".csv",".zip","/api/","results","report")):
            urls.add(absolute)
    for pattern in (
        r'''fetch\(["']([^"']+)["']''',
        r'''https?://[^"'\s<>]+(?:\.json|\.xml|\.csv|/api/[^"'\s<>]+)''',
    ):
        for match in re.findall(pattern,text,flags=re.I):
            urls.add(urljoin(base_url,match))
    return tuple(sorted(urls))


def is_scytl(url: str, body: bytes|None=None) -> bool:
    blob=url.lower()+" "+((body or b"")[:200000].decode("utf-8",errors="ignore").lower())
    return "scytl" in blob


def is_electionware(url: str, body: bytes|None=None) -> bool:
    blob=url.lower()+" "+((body or b"")[:200000].decode("utf-8",errors="ignore").lower())
    return "electionware" in blob
