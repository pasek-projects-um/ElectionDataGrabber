from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum

class AuditStatus(str, Enum):
    PARSED="parsed"
    PARTIAL="partial"
    STRUCTURALLY_UNRESOLVED="structurally_unresolved"
    UNREADABLE="unreadable"

@dataclass
class ArtifactAudit:
    source_url: str
    status: AuditStatus
    result_rows: int=0
    reporting_units: int=0
    contests: int=0
    candidates: int=0
    has_text_layer: bool | None=None
    reconciliation_error: float | None=None
    warnings: list[str]=field(default_factory=list)

def provisional_portability(a: ArtifactAudit) -> str:
    """Escalation heuristic; D/E remain provisional until family-level review."""
    if a.status == AuditStatus.PARSED and a.result_rows and a.reporting_units:
        return "A"
    if a.status == AuditStatus.PARTIAL:
        return "C"
    if a.status == AuditStatus.UNREADABLE and a.has_text_layer is False:
        return "D"
    if a.status == AuditStatus.STRUCTURALLY_UNRESOLVED:
        return "D"
    return "C"

def needs_escalation(a: ArtifactAudit) -> bool:
    if a.status in {AuditStatus.UNREADABLE, AuditStatus.STRUCTURALLY_UNRESOLVED}:
        return True
    if a.result_rows == 0:
        return True
    if a.reconciliation_error is not None and abs(a.reconciliation_error) > 0.005:
        return True
    return False
