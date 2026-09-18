# Canonical primary-locality coverage registry

The canonical locality registry is the source of truth for primary election locality identity and source-capability coverage. State and national coverage trackers are derived views, not independently maintained facts.

Each enumerated jurisdiction has one coverage state: enumerated unresolved, final only, election-night only, both, or affirmatively known missing. Estimated unknown units are the denominator remainder and are not represented by fake locality rows. A network, parser, or discovery failure cannot establish missing-source status.

Denominators live in a separate provenance-bearing registry. Changes to expected unit counts are therefore reviewable independently of locality enumeration and cannot silently create or delete jurisdictions.

Authority identity remains independent and is referenced by ID. Multiple localities may share one authority, and multiple sources/reporting regimes may belong to one locality without increasing the denominator. Reporting units from #14 are never denominator units.

The initial denominator file is a lossless migration of the existing planning tracker and is explicitly provisional. The locality registry starts empty rather than fabricating ID-level records from aggregate counts. Existing state registries and discovery reconciliation are inputs for subsequent evidence-backed population.

The generator enforces unique locality IDs, coverage/capability consistency, affirmative adjudication for known-missing status, per-state denominator bounds, and national sum invariants.
