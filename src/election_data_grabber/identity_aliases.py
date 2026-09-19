from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date
from pathlib import Path
import csv
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
        if when is None and (row.effective_from is not None or row.effective_to is not None):
            # Temporal aliases require an as-of date. Without one, selecting a
            # historical or future identity would manufacture a current mapping.
            continue
        if when is not None and ((row.effective_from and when < row.effective_from) or (row.effective_to and when > row.effective_to)):
            continue
        matches.append(row.canonical_id)
    unique = set(matches)
    if len(unique) > 1:
        return None
    return next(iter(unique), None)


def authoritative_external_alias(
    rows: list[IdentityAlias], canonical_id: str, *, namespace: str | None = None
) -> IdentityAlias | None:
    """Return a unique verified external alias; never choose arbitrarily across namespaces."""
    verified = [
        row for row in rows
        if row.canonical_id == canonical_id
        and row.alias_kind == AliasKind.EXTERNAL_ID
        and row.status == IdentityDecisionStatus.VERIFIED
        and (namespace is None or row.alias_namespace.strip().lower() == namespace.strip().lower())
    ]
    if not verified:
        return None
    unique = {(row.alias_namespace.strip().lower(), normalized_alias(row.alias_value)): row for row in verified}
    if len(unique) != 1:
        return None
    return next(iter(unique.values()))


ALIAS_FIELDS = (
    "object_type", "canonical_id", "alias_kind", "alias_value", "alias_namespace",
    "status", "confidence", "reconciliation_method", "evidence_reference",
    "reviewer", "effective_from", "effective_to",
)


def read_identity_aliases(path: Path) -> list[IdentityAlias]:
    if not path.exists():
        return []
    with path.open(encoding="utf-8-sig", newline="") as f:
        rows = []
        for raw in csv.DictReader(f):
            rows.append(IdentityAlias(
                object_type=IdentityObjectType(raw["object_type"]),
                canonical_id=raw["canonical_id"],
                alias_kind=AliasKind(raw["alias_kind"]),
                alias_value=raw["alias_value"],
                alias_namespace=raw["alias_namespace"],
                status=IdentityDecisionStatus(raw["status"]),
                confidence=float(raw["confidence"]) if raw.get("confidence") else None,
                reconciliation_method=raw["reconciliation_method"],
                evidence_reference=raw["evidence_reference"],
                reviewer=raw.get("reviewer") or None,
                effective_from=date.fromisoformat(raw["effective_from"]) if raw.get("effective_from") else None,
                effective_to=date.fromisoformat(raw["effective_to"]) if raw.get("effective_to") else None,
            ))
    validate_identity_aliases(rows)
    return rows


def write_identity_aliases(path: Path, rows: list[IdentityAlias]) -> None:
    """Persist an alias registry deterministically and without destructive identity rewrites."""
    validate_identity_aliases(rows)
    path.parent.mkdir(parents=True, exist_ok=True)
    ordered = sorted(rows, key=lambda row: (
        row.object_type.value, row.alias_namespace.lower(), normalized_alias(row.alias_value),
        row.canonical_id, row.alias_kind.value, row.status.value,
        row.effective_from or date.min, row.effective_to or date.max,
        row.alias_value,
    ))
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=ALIAS_FIELDS, lineterminator="\n")
        writer.writeheader()
        for row in ordered:
            writer.writerow({
                "object_type": row.object_type.value,
                "canonical_id": row.canonical_id,
                "alias_kind": row.alias_kind.value,
                "alias_value": row.alias_value,
                "alias_namespace": row.alias_namespace,
                "status": row.status.value,
                "confidence": "" if row.confidence is None else str(row.confidence),
                "reconciliation_method": row.reconciliation_method,
                "evidence_reference": row.evidence_reference,
                "reviewer": row.reviewer or "",
                "effective_from": row.effective_from.isoformat() if row.effective_from else "",
                "effective_to": row.effective_to.isoformat() if row.effective_to else "",
            })


def merge_identity_aliases(existing: list[IdentityAlias], additions: list[IdentityAlias]) -> list[IdentityAlias]:
    """Idempotently add decisions while refusing silent replacement of prior evidence."""
    merged = list(existing)
    for row in additions:
        if row not in merged:
            merged.append(row)
    validate_identity_aliases(merged)
    return merged
