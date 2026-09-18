# Election authority identity

Election authorities are administrative entities, not geographic jurisdictions. Their identity must therefore be independent of the jurisdiction or jurisdictions they serve.

## Canonical form

`us:authority:<state>:<authority-kind>:<key>`

A durable government-issued authority identifier is preferred for `key`. A normalized authority name is a provisional fallback.

An authority URL, vendor, current officeholder, or result artifact must never define authority identity.

## Geography relationship

Authority service geography is represented only through `authority_jurisdiction_crosswalk.csv`. Each row may have `effective_from` and `effective_to`, allowing:

- one authority to serve many jurisdictions;
- a jurisdiction to have multiple authorities when the administrative structure requires it;
- authority responsibility to change over time without rewriting historical identity.

The crosswalk requires evidence before production adjudication. Open-ended dates are permitted when the boundary is genuinely unknown or current.

## Migration

The older jurisdiction-scoped `authority_id(jurisdiction, kind)` helper on PR #11 is transitional. When this branch is reconciled with #11, national reconciliation should create independent authority IDs and emit crosswalk rows instead of embedding jurisdiction IDs inside authority IDs.
