# Snapshot provenance contract

Normalized election facts must be reproducible from immutable acquired bytes.

The compatibility contract is:

1. fetch;
2. persist a content-addressed `Snapshot`;
3. parse;
4. attach the snapshot SHA-256 to every normalized record;
5. call `require_snapshot_provenance` at persistence/export boundaries.

`source_id` is not sufficient provenance because a source can produce many snapshots over time. `fetched_at` is also not an immutable content identifier.

The current bridge deliberately leaves `snapshot_sha256` optional in Pydantic models so existing adapters remain compatible. New persistence paths must reject unlinked records. The later migration should change adapter APIs to parse a `Snapshot` (or a verified snapshot body/reference) directly, after which model-level provenance can become required.

Source timestamps remain distinct from fetch timestamps and snapshot identity.
