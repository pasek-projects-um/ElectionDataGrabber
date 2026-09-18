# Source capability registry

Primary-locality identity and denominator accounting remain in the canonical locality registry. Source capability is a separate evidence-bearing relation in `registry/jurisdiction_source_capabilities.csv`.

A locality may have multiple final and election-night sources without increasing its denominator count. Only positively adjudicated capability rows contribute to derived capability. Discovery candidates and platform fingerprints do not.

The initial migration preserves the five-state MI/OH/CT/PA/ME capability state exactly. Where the older locality registry had positive capability evidence but no normalized source ID, the migration uses a clearly marked `legacy:` source key rather than pretending the URL is identity. Those keys are migration placeholders to be replaced through source reconciliation without changing jurisdiction identity.

The national coverage tracker remains a generated view of canonical localities and denominators. Source capability records may eventually become the sole input for locality capability flags; during migration CI requires the two representations to agree exactly.
