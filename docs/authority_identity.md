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

Legacy jurisdiction-scoped authority identifiers may still appear in historical artifacts, but the current contract uses independent authority IDs plus explicit authority–jurisdiction crosswalk rows. New reconciliation work must not embed jurisdiction identity into authority identity.
