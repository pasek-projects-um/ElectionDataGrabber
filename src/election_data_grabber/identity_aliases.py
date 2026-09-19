from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date
from enum import StrEnum


TOKEN = re.compile(r"[^a-z0-9]+")


class IdentityObjectType(StrEnum):
    JURISDICTION = "jurisdiction"
    AUTHORITY = "authority"
    REPORTING_UNIT = "reporting_unit"


class AliasKind(StrEnum):
    HISTORICAL_ID = "historical_id"
    NAME = "name"
    EXTERNAL_ID = "external_id"


class IdentityDecisionStatus(StrEnum):
    PROPOSED = "proposed"
    VERIFIED = "verified"
    REJECTED = "rejected"
    AMBIGUOUS = "ambiguous"


def normalized_alias(value: str) -> str:
    return TOKEN.sub("-", value.strip().lower()).strip("-")


@dataclass(frozen=True, slots=True)
class IdentityAlias:
    object_type: IdentityObjectType
    canonical_id: str
    alias_kind: AliasKind
    alias_value: str
    alias_namespace: str
    status: IdentityDecisionStatus
    confidence: float | None
    reconciliation_method: str
    evidence_reference: str
    reviewer: str | None = None
    effective_from: date | None = None
    effective_to: date | None = None

    def __post_init__(self) -> None:
        if not self.canonical_id.strip() or not self.alias_value.strip() or not self.alias_namespace.strip():
            raise ValueError("canonical ID, alias value, and namespace are required")
        if self.confidence is not None and not 0 <= self.confidence <= 1:
            raise ValueError("confidence must be between zero and one")
        if not self.reconciliation_method.strip() or not self.evidence_reference.strip():
            raise ValueError("reconciliation method and evidence are required")
        if self.status == IdentityDecisionStatus.VERIFIED and not self.reviewer:
            raise ValueError("verified identity decision requires reviewer")
        if self.effective_from and self.effective_to and self.effective_to < self.effective_from:
            raise ValueError("effective_to cannot precede effective_from")

    @property
    def lookup_key(self) -> tuple[IdentityObjectType, str, str]:
        return self.object_type, self.alias_namespace.strip().lower(), normalized_alias(self.alias_value)


def _overlap(a0: date | None, a1: date | None, b0: date | None, b1: date | None) -> bool:
    return (a1 is None or b0 is None or b0 <= a1) and (b1 is None or a0 is None or a0 <= b1)


def validate_identity_aliases(rows: list[IdentityAlias]) -> None:
    exact_seen: set[tuple] = set()
    groups: dict[tuple[IdentityObjectType, str, str], list[IdentityAlias]] = {}
    for row in rows:
        exact = (
            row.object_type, row.canonical_id, row.alias_kind, row.alias_value,
            row.alias_namespace, row.status, row.confidence,
            row.reconciliation_method, row.evidence_reference, row.reviewer,
            row.effective_from, row.effective_to,
        )
        if exact in exact_seen:
            raise ValueError(f"duplicate identity alias decision: {row.lookup_key}")
        exact_seen.add(exact)
        groups.setdefault(row.lookup_key, []).append(row)
    for key, items in groups.items():
        verified = [row for row in items if row.status == IdentityDecisionStatus.VERIFIED]
        for i, left in enumerate(verified):
            for right in verified[i + 1:]:
                if left.canonical_id != right.canonical_id and _overlap(left.effective_from, left.effective_to, right.effective_from, right.effective_to):
                    raise ValueError(f"ambiguous verified alias collision: {key}")


def resolve_alias(rows: list[IdentityAlias], *, object_type: IdentityObjectType, namespace: str, value: str, when: date | None = None) -> str | None:
    validate_identity_aliases(rows)
    key = (object_type, namespace.strip().lower(), normalized_alias(value))
    matches = []
    for row in rows:
        if row.lookup_key != key or row.status != IdentityDecisionStatus.VERIFIED:
            continue
        if when is not None and ((row.effective_from and when < row.effective_from) or (row.effective_to and when > row.effective_to)):
            continue
        matches.append(row.canonical_id)
    unique = set(matches)
    if len(unique) > 1:
        return None
    return next(iter(unique), None)


def authoritative_external_alias(rows: list[IdentityAlias], canonical_id: str) -> IdentityAlias | None:
    verified = [
        row for row in rows
        if row.canonical_id == canonical_id
        and row.alias_kind == AliasKind.EXTERNAL_ID
        and row.status == IdentityDecisionStatus.VERIFIED
    ]
    if not verified:
        return None
    return sorted(verified, key=lambda row: (row.alias_namespace, row.alias_value))[0]
