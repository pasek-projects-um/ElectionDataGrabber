# Reporting topology integration

This package operationalizes canonical reporting-regime and reporting-unit identity in production adapter paths and introduces the explicit reporting-unit-to-geography bridge.

## Adapter contract

Adapters may receive an `AdapterReportingContext` carrying canonical jurisdiction, independent authority, canonical source identity/capability, election ID, regime kind, and immutable snapshot SHA.

When supplied, normalized observations must emit:

- canonical `jurisdiction_id`
- canonical `reporting_regime_id`
- canonical `reporting_unit_id`
- source-native/raw reporting-unit identity alongside the canonical ID

Election-night and certified/final feeds use distinct regime kinds and therefore distinct reporting-unit identities even if the source label is identical. Historical identities are not destructively rewritten.

The first-cut canaries cover Washtenaw/Michigan, the Ohio BOE precinct-detail family, a Pennsylvania precinct/division-shaped generic source, and Maine municipal ward/precinct topology.

## Geography bridge

`ReportingUnitGeographicCrosswalk` relates reporting topology to geography without conflating the two identities. Zero, one, or many mappings are supported.

Relationship semantics include exact, aggregate/component, split/merged, reassigned, synthetic/non-geographic, approximate, and unknown. Synthetic/non-geographic units cannot claim fake precinct geography. Allocation weights are optional and require an explicit evidence basis; they are never inferred merely to force reconciliation.

All crosswalks require immutable evidence snapshot provenance and support effective dating. Conflicting semantics for the same reporting/geographic pair during overlapping periods fail validation where determinable.

Maine wards/precincts remain reporting topology beneath the canonical municipality and never enter the primary-locality denominator.
