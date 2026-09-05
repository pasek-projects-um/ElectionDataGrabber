from __future__ import annotations
import json,re
from bs4 import BeautifulSoup
from urllib.parse import urljoin

URL_RE=re.compile(r'https?://[^\s\'"<>]+',re.I)
UNIT_WORDS={
"LA":("parish",),"MA":("city","town"),"MN":("county",),"ND":("county",),"NM":("county",),
"NY":("county","board of elections"),"RI":("board of canvassers","town","city"),"SC":("county",),
"VT":("town","city"),"WI":("clerk","county","town","village","city")
}

def structured_candidates(state:str, body:bytes, base_url:str)->list[str]:
    """Recover authority targets hidden in tables, data attributes, and JSON/script payloads."""
    soup=BeautifulSoup(body,"html.parser")
    words=UNIT_WORDS.get(state,())
    found=[]
    # Anchor extraction with parent-row/card context, not just anchor label.
    for a in soup.find_all("a",href=True):
        parent=a.find_parent(["tr","li","article","section","div"])
        context=" ".join(parent.stripped_strings) if parent else " ".join(a.stripped_strings)
        if not words or any(w in context.lower() for w in words):
            u=urljoin(base_url,str(a["href"]))
            if u.startswith("http"): found.append(u)
    # Many state directories hydrate from JSON or encode websites in data-* attributes.
    for tag in soup.find_all(True):
        for k,v in tag.attrs.items():
            vals=v if isinstance(v,list) else [v]
            for val in vals:
                if isinstance(val,str) and ("url" in k.lower() or "website" in k.lower()):
                    u=urljoin(base_url,val)
                    if u.startswith("http"): found.append(u)
    for script in soup.find_all("script"):
        text=script.string or script.get_text("",strip=False)
        if not text: continue
        for u in URL_RE.findall(text):
            if not re.search(r'(facebook|twitter|youtube|instagram|googleapis|schema\.org)',u,re.I):
                found.append(u.rstrip("\\,}]"))
    return list(dict.fromkeys(found))

def alaska_state_result_candidates(body:bytes,base_url:str)->list[str]:
    soup=BeautifulSoup(body,"html.parser"); out=[]
    for a in soup.find_all("a",href=True):
        blob=(" ".join(a.stripped_strings)+" "+str(a["href"])).lower()
        if re.search(r'(results?|election|precinct|district|summary|detail)',blob):
            out.append(urljoin(base_url,str(a["href"])))
    return list(dict.fromkeys(out))
