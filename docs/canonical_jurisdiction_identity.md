# Canonical jurisdiction and authority identity

Coverage accounting needs identity that is independent of URLs, vendor platforms, and individual election artifacts.

## Two IDs, not one

**jurisdiction_id** identifies the governmental/reporting jurisdiction.

Format:

`us:<state>:<level>:<key>`

Examples:

- `us:md:county:24031` when an authoritative GEOID/FIPS-like identifier is available.
- `us:wi:municipality:madison` as a fallback until a durable external identifier is attached.

**authority_id** identifies the election authority responsible for a jurisdiction.

Format:

`<jurisdiction_id>:authority:<authority-kind>:<ordinal>`

This separation is required because authority and geography are not universally one-to-one.

## Stability rules

1. Prefer durable government identifiers (Census GEOID/FIPS or state-issued identifiers) over names.
2. Never derive identity from a URL, hostname, vendor, current officeholder, or result artifact.
3. Preserve the original external identifier and its namespace in the canonical registry.
4. Name-derived keys are explicitly provisional and should be crosswalked—not silently replaced—when an authoritative identifier becomes available.
5. Authority changes over time belong in effective-date/crosswalk fields; historical records retain their original authority relationship.
6. Reporting units such as precincts are not primary-authority IDs. They remain in reporting topology.
7. Multi-jurisdiction authorities (for example a board serving multiple geographic units) require an explicit authority-to-jurisdiction crosswalk rather than duplicate invented authorities.

## Canonical registry target schema

The forthcoming locality registry should contain at least:

`jurisdiction_id, authority_id, state, jurisdiction_level, canonical_name, external_id_namespace, external_id, id_status, effective_from, effective_to, authority_kind, authority_name, source_url, evidence_url`

`id_status` is one of `authoritative_external`, `state_external`, or `provisional_name`.

Discovery observations reference these IDs after reconciliation. Raw observations remain immutable evidence and are never used as the canonical identity themselves.
