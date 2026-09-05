from __future__ import annotations
from dataclasses import dataclass


@dataclass(frozen=True)
class AdministrativePath:
    """Election-specific reporting hierarchy; levels may be absent or repeated."""
    state: str
    county: str | None = None
    municipality: str | None = None
    ward: str | None = None
    precinct: str | None = None
    reporting_unit: str | None = None
    subunit: str | None = None


def reconciliation_keys(path: AdministrativePath) -> list[tuple[str, str]]:
    """Return every distinct aggregation key available on a reporting path."""
    pairs=[
        ("state",path.state),("county",path.county),("municipality",path.municipality),
        ("ward",path.ward),("precinct",path.precinct),("reporting_unit",path.reporting_unit),
        ("subunit",path.subunit),
    ]
    out=[]
    seen=set()
    for level,value in pairs:
        if value and (level,value) not in seen:
            out.append((level,value)); seen.add((level,value))
    return out


def maine_reconciliation_keys(path: AdministrativePath) -> list[tuple[str, str]]:
    """Backward-compatible Maine alias."""
    return reconciliation_keys(path)
