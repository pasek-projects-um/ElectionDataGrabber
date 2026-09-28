# Source capability registry

Primary-locality identity and denominator accounting remain in the canonical locality registry. Source capability is a separate evidence-bearing relation in `registry/jurisdiction_source_capabilities.csv`.

A locality may have multiple final and election-night sources without increasing its denominator count. A single source may expose multiple capabilities. Capability type is therefore not part of source identity. Only positively adjudicated capability rows contribute to derived capability; discovery candidates, rejected evidence, and platform fingerprints do not.

## Historical migration note

The first capability migration preserved the then-existing MI/OH/CT/PA/ME state exactly. That five-state scope is historical context, not the current national coverage boundary. Older positive evidence without a normalized source ID may still use a clearly marked `legacy:` source key; these keys are migration placeholders, not a durable source namespace, and URLs are never promoted to identity.

Every migrated row carries an explicit registry evidence reference. Future source adjudication should replace that with immutable snapshot provenance where available. Replacement of a legacy source key must preserve the capability evidence/history rather than rewriting jurisdiction identity.

## Temporal and validation contract

Capability validity can be effective-dated. Overlapping periods for the same jurisdiction/source/capability are rejected; historical source replacement is represented as separate, non-overlapping records. Derivation can be evaluated for a particular date. A positive capability requires explicit verification status and provenance.

A capability must bind to a canonical locality and its independent election authority. The authority-jurisdiction crosswalk remains the authoritative relationship layer; the source-capability registry does not redefine authority identity. Future normalized source IDs may legitimately be shared across jurisdictions or authorities when one upstream source serves several jurisdictions.

## Coverage compatibility

The national coverage tracker is a generated view of canonical localities and denominators. Positive final/election-night coverage derives from the first-class source-capability relation; compatibility fields may remain readable for older consumers but are not authoritative inputs to generated positive coverage. `known_missing_source` remains an explicit locality adjudication because absence of a positive source relation is not evidence of absence. Catalogued state surfaces, candidate leads, platform fingerprints, and execution readiness are separate evidence layers and do not by themselves create positive locality capability.

Failed fetches, parser failures, discovery misses, and unsupported artifacts do not establish source absence and cannot create a positive capability or `known_missing_source`.
