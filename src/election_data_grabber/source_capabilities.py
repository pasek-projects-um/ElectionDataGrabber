from __future__ import annotations
import csv
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

class CapabilityType(StrEnum):
    FINAL = "final"
    ELECTION_NIGHT = "election_night"

POSITIVE_STATUSES = {"verified", "affirmatively_adjudicated", "migrated_positive"}

@dataclass(frozen=True, slots=True)
class JurisdictionSourceCapability:
    jurisdiction_id: str
    authority_id: str
    source_id: str
    capability_type: CapabilityType
    source_url: str = ""
    platform_family: str = ""
    smallest_observed_unit: str = ""
    valid_from: str = ""
    valid_to: str = ""
    evidence_snapshot_sha256: str = ""
    verification_status: str = ""
    assessment_method: str = ""
    evidence_reference: str = ""
    notes: str = ""

    def __post_init__(self) -> None:
        if not self.jurisdiction_id.startswith("us:"):
            raise ValueError("source capability requires canonical jurisdiction_id")
        if self.authority_id and not self.authority_id.startswith("us:authority:"):
            raise ValueError("source capability authority_id must use independent namespace")
        if not self.source_id:
            raise ValueError("source capability requires source_id")
        if not self.assessment_method:
            raise ValueError("source capability requires assessment_method")
        if self.evidence_snapshot_sha256 and (len(self.evidence_snapshot_sha256) != 64 or any(c not in "0123456789abcdefABCDEF" for c in self.evidence_snapshot_sha256)):
            raise ValueError("evidence_snapshot_sha256 must be a SHA-256 hex digest")
        if self.valid_from and self.valid_to and self.valid_from > self.valid_to:
            raise ValueError("source capability validity interval is inverted")
        if not self.evidence_snapshot_sha256 and not self.evidence_reference:
            raise ValueError("source capability requires evidence provenance")

def read_source_capabilities(path: Path) -> list[JurisdictionSourceCapability]:
    with path.open(encoding="utf-8-sig", newline="") as f:
        return [JurisdictionSourceCapability(
            jurisdiction_id=r["jurisdiction_id"], authority_id=r.get("authority_id",""),
            source_id=r["source_id"], capability_type=CapabilityType(r["capability_type"]),
            source_url=r.get("source_url",""), platform_family=r.get("platform_family",""),
            smallest_observed_unit=r.get("smallest_observed_unit",""), valid_from=r.get("valid_from",""),
            valid_to=r.get("valid_to",""), evidence_snapshot_sha256=r.get("evidence_snapshot_sha256",""),
            verification_status=r.get("verification_status",""), assessment_method=r.get("assessment_method",""),
            evidence_reference=r.get("evidence_reference",""), notes=r.get("notes","")) for r in csv.DictReader(f)]

def validate_source_capabilities(rows: list[JurisdictionSourceCapability]) -> None:
    seen=set()
    for r in rows:
        key=(r.jurisdiction_id,r.authority_id,r.source_id,r.capability_type,r.valid_from,r.valid_to)
        if key in seen: raise ValueError(f"duplicate source capability: {key}")
        seen.add(key)

def derived_capabilities(rows: list[JurisdictionSourceCapability]) -> dict[str, tuple[bool,bool]]:
    validate_source_capabilities(rows)
    out={}
    for r in rows:
        if r.verification_status not in POSITIVE_STATUSES:
            continue
        final,live=out.get(r.jurisdiction_id,(False,False))
        if r.capability_type is CapabilityType.FINAL: final=True
        if r.capability_type is CapabilityType.ELECTION_NIGHT: live=True
        out[r.jurisdiction_id]=(final,live)
    return out


def validate_locality_bindings(rows: list[JurisdictionSourceCapability], localities: list[object]) -> None:
    by_id = {getattr(r, "jurisdiction_id"): r for r in localities}
    for capability in rows:
        locality = by_id.get(capability.jurisdiction_id)
        if locality is None:
            raise ValueError(f"source capability references unknown locality: {capability.jurisdiction_id}")
        expected_authority = getattr(locality, "authority_id", "")
        if capability.authority_id != expected_authority:
            raise ValueError(f"source capability authority disagrees with locality: {capability.jurisdiction_id}")
