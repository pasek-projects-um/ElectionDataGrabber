# Identity aliases and governed vote modes

## Persistent identity aliases

Canonical IDs are durable observation keys. Adoption of an authoritative external ID must not rewrite historical observations or discard the provisional ID that originally carried evidence.

`IdentityAlias` records locality, authority, and reporting-unit aliases with a namespace, alias kind, effective interval, decision status, confidence, reconciliation method, evidence, and reviewer. Only verified aliases resolve automatically. A normalized textual match is never itself sufficient evidence. Two different canonical objects cannot hold the same verified namespace/value alias during an overlapping interval.

Historical names and provisional IDs therefore remain queryable after authoritative external-ID adoption. Reconciliation is additive and idempotent rather than a destructive ID migration. `read_identity_aliases` / `write_identity_aliases` provide a deterministic CSV persistence boundary, and `merge_identity_aliases` makes reruns additive while collision validation prevents an authoritative external alias from being silently repointed. An overlapping verified alias also cannot be downgraded to a proposed, rejected, or ambiguous decision on a later rerun.

## Governed vote modes

Adapters preserve the raw source label and resolve it through `VoteModeRule`. Rules may be global, state-specific, or source-specific; the most specific verified rule wins. Candidate/rejected rules never promote observations.

Unknown labels remain `VoteMode.UNKNOWN` at normalization boundaries rather than becoming `OTHER` or a convenient known mode. Mapping method and evidence reference travel with normalized observations.

`TOTAL` is an aggregate, not another additive vote mode. Aggregation paths must choose either aggregate totals or known component modes when both coexist; they must not sum both. `UNKNOWN`/`OTHER` do not claim component semantics and therefore cannot by themselves prove that a `TOTAL` row is being double-counted.

Michigan `AV` is deliberately state-scoped. It is not treated as a universal synonym for absentee/mail. Maine/document and other source-specific semantics should be added only when evidence establishes the meaning of the source label.
