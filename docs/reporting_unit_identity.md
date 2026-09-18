# Canonical reporting-unit identity

Reporting units describe source reporting topology, not durable geography. IDs are scoped to an election and reporting regime; raw labels are never sufficient evidence of cross-election continuity.

A reporting regime binds an election, canonical jurisdiction, independent election authority, source capability, source, and immutable snapshot. Election-night, certified, recount/corrected, and historical representations therefore remain distinct.

Canonical reporting units retain raw and canonical names, source-native IDs when available, aggregation scope, allocation semantics, identity status, reconciliation status, parent topology, effective dates, and immutable snapshot provenance. Identity status and reconciliation status are deliberately separate.

Cross-election or cross-regime continuity is represented with explicit provenance-bearing crosswalks. Relationships include same-as, rename, split, merge, aggregate/component, reassignment, and approximate crosswalk. Weights are optional and require an explicit evidence basis; the model never manufactures weights merely to force reconciliation.

This package does not create primary-locality identities or mutate locality coverage denominators. Production reporting regimes must consume the canonical locality/source-capability layer owned by #15. It also does not project certified topology backward onto election-night feeds.

Migration is additive: existing ReportingUnit and ResultObservation records remain valid while adapter families begin emitting reporting regimes and canonical reporting-unit identities. Historical identities are crosswalked rather than destructively rewritten.
