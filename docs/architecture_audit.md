# Architecture audit — acquisition, identity, provenance, and reconciliation

**Date:** 2026-09-17  
**Scope:** canonical models; fetch/snapshot layer; generic discovery; authority/artifact audit; canonical IDs; national reconciliation/accounting; generic CSV/HTML; Enhanced Voting, Clarity, CivicPlus, and standardized tabulator-report adapters.

## Executive assessment

The codebase has a sound separation of acquisition, discovery, and normalization for an exploratory national system, but the audit found several contracts that must be hardened before coverage is scaled aggressively. Three correctness risks were fixed immediately in this audit. Two architectural issues should block treating national coverage as production-grade until resolved.

Severity vocabulary: **P0 invariant violation**, **P1 correctness risk**, **P2 scalability/reproducibility risk**, **P3 technical debt**.

## Findings

### A-01 — Generic CSV promoted result-column order to ballot order — P0 — FIXED

The generic CSV adapter accepted `ballot_order`, `order`, and `position` as authoritative voter-facing ballot order. This violated the project's explicit rule that result/display order is not ballot order without authoritative ballot/rotation evidence.

**Fix:** generic CSV now writes these ambiguous fields to `source_order`. Authoritative ballot order must come from a ballot-specific adapter/evidence path.

### A-02 — Reconciliation silently truncated identity overflow — P0 — FIXED

The national reconciler sorted inferred jurisdictions and sliced them to the state's planning denominator. If heuristics produced too many identities, arbitrary IDs could therefore be accepted while others silently disappeared.

**Fix:** overflow now fails closed and requires profile/identity review.

### A-03 — Aggregate tracker update is not safe after capability adjudication — P0 — FIXED/guarded

Reconciliation recomputed `enumerated_unresolved` from discovery while preserving aggregate capability counts. Once any units were adjudicated, the same jurisdiction could be counted both unresolved and adjudicated because there was no ID-level join.

**Fix:** the reconciler now refuses to rewrite a state with existing aggregate adjudication. The durable solution is an ID-level canonical locality registry from which aggregate tracker counts are derived.

### A-04 — Normalized facts are not obligatorily linked to immutable snapshots — P1 — PARTIAL

`Snapshot` is content-addressed, but `ResultObservation` and `BallotSummary` historically carried only `source_id` and timestamps. A source can produce many snapshots, so those fields do not uniquely identify the bytes from which a normalized fact was extracted.

**Immediate change:** optional `snapshot_sha256` provenance hooks were added to both normalized models.

**Required follow-up:** normalized persistence should require a snapshot hash (or snapshot ID) and adapters should parse from persisted snapshots, not free-floating response bodies. Source timestamps should also be captured from authoritative payload/header evidence rather than inferred.

### A-05 — Authority identity is still jurisdiction-scoped — P1 — OPEN

The documentation correctly states that one election authority may serve multiple jurisdictions, but `authority_id()` is constructed underneath a jurisdiction ID. That representation cannot naturally give one stable authority identity to a multi-jurisdiction board without choosing an arbitrary parent or duplicating the authority.

**Required:** introduce an authority namespace independent of jurisdiction and an effective-dated authority↔jurisdiction crosswalk before multi-jurisdiction cases are canonicalized.

### A-06 — Provisional name IDs need a persistent alias/crosswalk registry — P1 — OPEN

Name-derived jurisdiction IDs are correctly labeled provisional, but there is not yet a persisted alias/supersession table. Replacing a provisional ID with GEOID/state ID could orphan prior discovery/reconciliation records.

**Required:** canonical registry plus alias table; never mutate historical IDs in place.

### A-07 — Reporting-unit IDs are raw-name concatenations — P1 — OPEN

Generic and Enhanced Voting adapters form reporting-unit IDs from `jurisdiction_id + raw unit name`. This is vulnerable to punctuation/case changes, duplicate names, renames, and election-to-election topology changes.

**Required:** canonical/election-scoped reporting-unit identity with raw labels retained separately and temporal crosswalks where units persist/change.

### A-08 — Adapter provenance contract is inconsistent — P2 — OPEN

The abstract adapter contract parses `body: bytes` plus `fetched_at`, while snapshots are a separate operation. Nothing forces callers to snapshot before parsing. This makes reproducibility a convention rather than an invariant.

**Required:** add a parse-from-snapshot/persist-normalized boundary and tests that every persisted observation references an existing immutable snapshot.

### A-09 — Vote-mode inference is appropriately conservative in some adapters but not centrally governed — P2 — OPEN

Enhanced Voting and generic parsers map explicit labels/keys, which is directionally correct. However there is no shared evidence policy distinguishing literal source labels from adapter-derived mappings or jurisdiction-specific semantics.

**Required:** central vote-mode mapping/evidence metadata; preserve `raw_vote_mode` and mapping method/confidence.

### A-10 — Election-night completeness semantics are under-modeled — P2 — OPEN

`precincts_reporting/precincts_total` exist on observations, but unit presence, component completeness, aggregation scope, cumulative-update semantics, and source-reported completion are not represented as a common normalized contract.

**Required:** model reporting progress separately from vote observations, preserving scope and allocation semantics.

### A-11 — Discovery heuristics are evidence generators, not authority verification — P2 — OPEN

Authority discovery scores election-like links and gives a bonus to .gov hosts, but it does not itself establish official ownership. The national reconciler appropriately remains conservative, but the distinction needs to stay explicit as automation expands.

**Required:** provenance for verification method and an explicit adjudication state before a discovered URL becomes an official source.

### A-12 — Artifact portability grades are heuristic and should not become data quality scores — P3 — OPEN

The A/C/D/E provisional heuristic is useful for triage, but `reconciliation_error` and parseability do not fully characterize semantic correctness.

**Required:** keep portability separate from semantic validation/assurance; document family-specific acceptance tests.

## Contract tests to add next

1. Every persisted normalized observation resolves to an immutable snapshot.
2. Generic result adapters cannot set `ballot_order` without an explicit authoritative-ballot profile.
3. Reconciliation is idempotent across repeated identical runs.
4. A canonical jurisdiction appears in exactly one coverage capability state.
5. Coverage aggregates are derived from ID-level records, not independently edited totals.
6. Authority↔jurisdiction crosswalk supports one-to-many and effective dates.
7. Reporting-unit identity remains distinct from raw display label.
8. Election-night topology cannot be inferred from certified/final topology.
9. Null registration remains null for no-registration regimes.
10. Vote-mode mappings retain raw label and mapping evidence.

## Recommended sequence

1. Build the canonical locality registry and derive coverage aggregates from it.
2. Decouple authority IDs from jurisdiction IDs and add authority↔jurisdiction crosswalks.
3. Make snapshot linkage mandatory at normalized persistence.
4. Canonicalize/election-scope reporting-unit identity.
5. Add shared vote-mode and reporting-progress semantics.
6. Resume broad state expansion after these contracts are executable.

## Audit conclusion

No evidence from this review suggests the existing state work should be discarded. The main risk is that exploratory conventions could become de facto national contracts. The immediate fixes remove three concrete invariant violations; the remaining P1 items should be resolved before the tracker is treated as authoritative national coverage.
