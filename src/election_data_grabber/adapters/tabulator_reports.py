from __future__ import annotations
import re
from dataclasses import dataclass

REPORT_NAMES=re.compile(r"(statement\s+of\s+votes\s+cast|election\s+summary\s+report|canvass\s+results?\s+report)",re.I)
PRECINCTS=re.compile(r"precincts?\s+report(?:ed|ing)\s*[:\-]?\s*(\d+)\s+(?:of|/|out\s+of)\s+(\d+)",re.I)
TURNOUT=re.compile(r"(registered\s+voters|voters\s+cast|ballots\s+cast|turnout)",re.I)
MODES=re.compile(r"(election\s+day|absentee|early\s+voting|provisional|mail)",re.I)

@dataclass(frozen=True)
class TabulatorReportProfile:
    family: str
    precincts_reported: int|None
    precincts_total: int|None
    has_turnout: bool
    vote_modes: tuple[str,...]

def profile_tabulator_report(text: str) -> TabulatorReportProfile|None:
    m=REPORT_NAMES.search(text)
    if not m: return None
    p=PRECINCTS.search(text)
    modes=tuple(dict.fromkeys(x.lower() for x in MODES.findall(text)))
    return TabulatorReportProfile(
        family=re.sub(r"\s+","_",m.group(1).lower()),
        precincts_reported=int(p.group(1)) if p else None,
        precincts_total=int(p.group(2)) if p else None,
        has_turnout=bool(TURNOUT.search(text)),
        vote_modes=modes,
    )
