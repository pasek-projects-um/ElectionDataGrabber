from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass

VALID_LEVELS = {
    "state", "county", "county_equivalent", "parish", "borough",
    "municipality", "town", "city", "ward", "election_authority",
}
SAFE = re.compile(r"[^a-z0-9]+")


def _token(value: str) -> str:
    value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode()
    return SAFE.sub("-", value.lower()).strip("-")


def jurisdiction_id(state: str, level: str, canonical_name: str, external_id: str = "") -> str:
    """Return a deterministic jurisdiction ID.

    Prefer a durable government identifier (normally Census/FIPS/GEOID) when
    one exists. The name token is a fallback key, not an assertion that names
    never change.
    """
    st = state.strip().upper()
    lvl = _token(level)
    if not re.fullmatch(r"[A-Z]{2}", st):
        raise ValueError(f"invalid state abbreviation: {state!r}")
    if level not in VALID_LEVELS:
        raise ValueError(f"unsupported jurisdiction level: {level!r}")
    key = _token(external_id) if external_id.strip() else _token(canonical_name)
    if not key:
        raise ValueError("canonical_name or external_id is required")
    return f"us:{st.lower()}:{lvl}:{key}"


def authority_id(jurisdiction: str, authority_kind: str, ordinal: int = 1) -> str:
    """Return a stable authority ID scoped to a canonical jurisdiction.

    Authority is intentionally separate from jurisdiction: one jurisdiction
    can have multiple election authorities and one authority may later be
    crosswalked to multiple jurisdictions.
    """
    kind = _token(authority_kind)
    if not jurisdiction.startswith("us:") or not kind or ordinal < 1:
        raise ValueError("invalid authority identity inputs")
    return f"{jurisdiction}:authority:{kind}:{ordinal}"


@dataclass(frozen=True)
class CanonicalAuthority:
    jurisdiction_id: str
    authority_id: str
    state: str
    jurisdiction_level: str
    canonical_name: str
    external_id: str = ""
