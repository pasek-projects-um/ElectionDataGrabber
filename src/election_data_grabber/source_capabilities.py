from __future__ import annotations

import csv
import re
from dataclasses import dataclass
from datetime import date
from enum import StrEnum
from pathlib import Path


class CapabilityType(StrEnum):
    FINAL = "final"
    ELECTION_NIGHT = "election_night"


class VerificationStatus(StrEnum):
    CANDIDATE = "candidate"
    VERIFIED = "verified"
    AFFIRMATIVELY_ADJUDICATED = "affirmatively_adjudicated"
    MIGRATED_POSITIVE = "migrated_positive"
    REJECTED = "rejected"


POSITIVE_STATUSES = {
    VerificationStatus.VERIFIED,
    VerificationStatus.AFFIRMATIVELY_ADJUDICATED,
    VerificationStatus.MIGRATED_POSITIVE,
}
_SHA256 = re.compile(r"^[0-9a-f]{64}$")


@dataclass(frozen=True, slots=True)
class JurisdictionSourceCapability:
    jurisdiction_id: str
    authority_id: str
    source_id: str
    capability_type: CapabilityType
    source_url: str = ""
    platform_family: str = ""
    smallest_observed_unit: str = ""
    valid_from: date | None = None
    valid_to: date | None = None
    evidence_snapshot_sha256: str = ""
    verification_status: VerificationStatus = VerificationStatus.CANDIDATE
    assessment_method: str = ""
    evidence_reference: str = ""
    notes: str = ""

    def __post_init__(self) -> None:
        if not self.jurisdiction_id.startswith("us:"):
            raise ValueError("source capability requires canonical jurisdiction_id")
        if not self.authority_id.startswith("us:authority:"):
            raise ValueError("source capability requires independent authority_id")
        if not self.source_id.strip():
            raise ValueError("source capability requires source_id")
        if not self.assessment_method.strip():
            raise ValueError("source capability requires assessment_method")
        digest = self.evidence_snapshot_sha256.lower()
        if digest and not _SHA256.fullmatch(digest):
            raise ValueError("evidence_snapshot_sha256 must be a SHA-256 hex digest")
        if self.valid_from and self.valid_to and self.valid_to < self.valid_from:
            raise ValueError("source capability validity interval is inverted")
        if not digest and not self.evidence_reference.strip():
            raise ValueError("source capability requires evidence provenance")

    @property
    def is_positive(self) -> bool:
        return self.verification_status in POSITIVE_STATUSES

    def active_on(self, when: date) -> bool:
        if self.valid_from and when < self.valid_from:
            return False
        if self.valid_to and when > self.valid_to:
            return False
        return True


def _date(value: str) -> date | None:
    return date.fromisoformat(value) if value.strip() else None


def read_source_capabilities(path: Path) -> list[JurisdictionSourceCapability]:
    with path.open(encoding="utf-8-sig", newline="") as f:
        return [
            JurisdictionSourceCapability(
                jurisdiction_id=r["jurisdiction_id"],
                authority_id=r["authority_id"],
                source_id=r["source_id"],
                capability_type=CapabilityType(r["capability_type"]),
                source_url=r.get("source_url", ""),
                platform_family=r.get("platform_family", ""),
                smallest_observed_unit=r.get("smallest_observed_unit", ""),
                valid_from=_date(r.get("valid_from", "")),
                valid_to=_date(r.get("valid_to", "")),
                evidence_snapshot_sha256=r.get("evidence_snapshot_sha256", ""),
                verification_status=VerificationStatus(r.get("verification_status", "candidate")),
                assessment_method=r.get("assessment_method", ""),
                evidence_reference=r.get("evidence_reference", ""),
                notes=r.get("notes", ""),
            )
            for r in csv.DictReader(f)
        ]


def validate_source_capabilities(rows: list[JurisdictionSourceCapability]) -> None:
    seen: set[tuple[object, ...]] = set()
    groups: dict[tuple[str, str, CapabilityType], list[JurisdictionSourceCapability]] = {}
    source_owners: dict[str, tuple[str, str]] = {}
    for r in rows:
        key = (r.jurisdiction_id, r.authority_id, r.source_id, r.capability_type, r.valid_from, r.valid_to)
        if key in seen:
            raise ValueError(f"duplicate source capability: {key}")
        seen.add(key)
        groups.setdefault((r.jurisdiction_id, r.source_id, r.capability_type), []).append(r)

        # Legacy migration IDs are intentionally jurisdiction-scoped. Future normalized
        # source IDs may be shared by several jurisdictions/authorities and are not
        # constrained here.
        if r.source_id.startswith("legacy:"):
            owner = (r.jurisdiction_id, r.authority_id)
            previous = source_owners.setdefault(r.source_id, owner)
            if previous != owner:
                raise ValueError(f"legacy source_id reused across owners: {r.source_id}")

    for key, items in groups.items():
        ordered = sorted(items, key=lambda r: r.valid_from or date.min)
        for previous, current in zip(ordered, ordered[1:]):
            previous_end = previous.valid_to or date.max
            current_start = current.valid_from or date.min
            if current_start <= previous_end:
                raise ValueError(f"overlapping source-capability validity periods: {key}")


def derived_capabilities(
    rows: list[JurisdictionSourceCapability],
    *,
    when: date | None = None,
) -> dict[str, tuple[bool, bool]]:
    validate_source_capabilities(rows)
    out: dict[str, tuple[bool, bool]] = {}
    for r in rows:
        if not r.is_positive or (when is not None and not r.active_on(when)):
            continue
        final, live = out.get(r.jurisdiction_id, (False, False))
        if r.capability_type is CapabilityType.FINAL:
            final = True
        elif r.capability_type is CapabilityType.ELECTION_NIGHT:
            live = True
        out[r.jurisdiction_id] = (final, live)
    return out


def validate_locality_bindings(
    rows: list[JurisdictionSourceCapability],
    localities: list[object],
    authority_crosswalks: list[object] | None = None,
) -> None:
    by_id = {getattr(r, "jurisdiction_id"): r for r in localities}
    if len(by_id) != len(localities):
        raise ValueError("duplicate canonical locality while validating source capabilities")

    valid_pairs = None
    if authority_crosswalks is not None:
        valid_pairs = {
            (getattr(r, "authority_id"), getattr(r, "jurisdiction_id"))
            for r in authority_crosswalks
        }

    for capability in rows:
        locality = by_id.get(capability.jurisdiction_id)
        if locality is None:
            raise ValueError(f"source capability references unknown locality: {capability.jurisdiction_id}")
        expected_authority = getattr(locality, "authority_id", "")
        if capability.authority_id != expected_authority:
            raise ValueError(f"source capability authority disagrees with locality: {capability.jurisdiction_id}")
        if valid_pairs is not None and (capability.authority_id, capability.jurisdiction_id) not in valid_pairs:
            raise ValueError(f"source capability lacks authority-jurisdiction crosswalk: {capability.jurisdiction_id}")
