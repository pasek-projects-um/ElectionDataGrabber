from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from datetime import date

SAFE = re.compile(r"[^a-z0-9]+")


def _token(value: str) -> str:
    value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode()
    return SAFE.sub("-", value.lower()).strip("-")


def election_authority_id(
    state: str,
    authority_kind: str,
    canonical_name: str,
    external_id: str = "",
) -> str:
    """Stable election-authority identity independent of served geography.

    Prefer a durable government-issued authority identifier. Name-derived keys
    are provisional and must be crosswalked rather than silently replaced.
    """
    st = state.strip().upper()
    if not re.fullmatch(r"[A-Z]{2}", st):
        raise ValueError(f"invalid state abbreviation: {state!r}")
    kind = _token(authority_kind)
    key = _token(external_id) if external_id.strip() else _token(canonical_name)
    if not kind or not key:
        raise ValueError("authority_kind and canonical_name/external_id are required")
    return f"us:authority:{st.lower()}:{kind}:{key}"


@dataclass(frozen=True, slots=True)
class AuthorityJurisdictionCrosswalk:
    authority_id: str
    jurisdiction_id: str
    effective_from: date | None = None
    effective_to: date | None = None
    evidence_url: str | None = None

    def __post_init__(self) -> None:
        if not self.authority_id.startswith("us:authority:"):
            raise ValueError("authority_id must use independent authority namespace")
        if not self.jurisdiction_id.startswith("us:"):
            raise ValueError("jurisdiction_id must be canonical")
        if self.effective_from and self.effective_to and self.effective_to < self.effective_from:
            raise ValueError("effective_to cannot precede effective_from")

    def active_on(self, when: date) -> bool:
        if self.effective_from and when < self.effective_from:
            return False
        if self.effective_to and when > self.effective_to:
            return False
        return True


def validate_crosswalks(rows: list[AuthorityJurisdictionCrosswalk]) -> None:
    """Reject duplicate/overlapping effective periods for the same relationship."""
    groups: dict[tuple[str, str], list[AuthorityJurisdictionCrosswalk]] = {}
    for row in rows:
        groups.setdefault((row.authority_id, row.jurisdiction_id), []).append(row)
    for key, items in groups.items():
        ordered = sorted(items, key=lambda r: r.effective_from or date.min)
        for previous, current in zip(ordered, ordered[1:]):
            prev_end = previous.effective_to or date.max
            cur_start = current.effective_from or date.min
            if cur_start <= prev_end:
                raise ValueError(f"overlapping authority-jurisdiction periods: {key}")
