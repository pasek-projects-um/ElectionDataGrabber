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


def maine_reconciliation_keys(path: AdministrativePath) -> list[tuple[str, str]]:
    """Return aggregation keys available for Maine statewide/local reconciliation."""
    keys=[("state",path.state)]
    if path.county:
        keys.append(("county",path.county))
    if path.municipality:
        keys.append(("municipality",path.municipality))
    if path.ward:
        keys.append(("ward",path.ward))
    if path.precinct:
        keys.append(("precinct",path.precinct))
    if path.reporting_unit and path.reporting_unit not in {path.precinct,path.ward,path.municipality}:
        keys.append(("reporting_unit",path.reporting_unit))
    return keys
