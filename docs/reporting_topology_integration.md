# Reporting topology integration

This package operationalizes canonical reporting-regime and reporting-unit identity in production adapter paths and introduces the explicit reporting-unit-to-geography bridge.

## Adapter contract

A `ReportingContextSpec` is built from a positively adjudicated jurisdiction-source capability before fetch. Each persisted snapshot then materializes an `AdapterReportingContext` carrying canonical jurisdiction, independent authority, canonical source identity/capability, election ID, regime kind, and that snapshot's immutable SHA. Context construction rejects capability/regime mismatches.

When supplied, normalized observations must emit:

- canonical `jurisdiction_id`
- canonical `reporting_regime_id`
- canonical `reporting_unit_id`
- source-native/raw reporting-unit identity alongside the canonical ID

Election-night and certified/final feeds use distinct regime kinds and therefore distinct reporting-unit identities even if the source label is identical. Historical identities are not destructively rewritten.

The migration covers Washtenaw production ingest and shared Washtenaw-like, Ohio BOE precinct-detail, generic CSV/JSON/HTML, Enhanced Voting, and Clarity-like adapter paths. Structural canaries cover Washtenaw/Michigan, the Ohio BOE family, a Pennsylvania precinct/division-shaped source, and Maine municipal ward/precinct topology. Generic result/display order is preserved as `source_order`, never promoted to voter-facing `ballot_order` without separate ballot evidence.

## Geography bridge

`ReportingUnitGeographicCrosswalk` relates reporting topology to geography without conflating the two identities. Zero, one, or many mappings are supported.

Relationship semantics include exact, aggregate/component, split/merged, reassigned, synthetic/non-geographic, approximate, and unknown. Synthetic/non-geographic units cannot claim fake precinct geography. Allocation weights are optional and require an explicit evidence basis; they are never inferred merely to force reconciliation. Weighted mappings explicitly distinguish `complete`, `partial`, and `unknown` coverage. A complete allocation must sum to 1, but partial/unknown geography may legitimately sum below 1 when votes are retained in source-native non-geographic pools (for example mail/absentee counting units) or when small/suppressed areas cannot be cleanly assigned. A source-reported residual may be preserved as an explicit unmapped share; otherwise the residual stays unknown rather than being fabricated into geography.

All crosswalks require immutable evidence snapshot provenance and support effective dating. Conflicting semantics for the same reporting/geographic pair during overlapping periods fail validation where determinable.

Maine wards/precincts remain reporting topology beneath the canonical municipality and never enter the primary-locality denominator.
