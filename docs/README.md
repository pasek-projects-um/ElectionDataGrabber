# Documentation map

Documentation falls into three categories. The distinction matters because many state investigations were written while the project was much narrower.

## Current architecture and operating contracts

These describe the system as it should behave now:

- `../README.md` — current project scope and pipeline.
- `../ROADMAP.md` — current milestones and priorities.
- `data_model_principles.md` — normalization/geography/provenance principles.
- `canonical_jurisdiction_identity.md` and `authority_identity.md` — durable jurisdiction/authority identity.
- `locality_registry.md`, `local_unit_coverage_tracker.md`, and `source_capabilities.md` — denominator/capability accounting.
- `geographic_source_evidence_ledger.md` — geography-first source evidence and external lead policy.
- `reporting_topology.md`, `reporting_unit_identity.md`, and `reporting_topology_integration.md` — election-night/final reporting topology.
- `snapshot_provenance.md` — immutable acquisition-to-normalization provenance.
- `identity_aliases_vote_modes.md` — temporal identity aliases and governed vote-mode semantics.
- `jurisdiction_coverage.md` — coverage dimensions and precinct/reporting-unit discovery.
- `integrity_assurance.md` and `model_target.md` — downstream analytical/assurance targets, not acquisition-coverage claims.
- `pdf_extraction_strategy.md` — document extraction escalation policy.

## Dated audits and design snapshots

- `architecture_audit.md` is explicitly dated 2026-09-17. Its findings are valuable provenance, but “next”/open-status language should be interpreted as of that audit date.
- `national_local_reporting_source_census.md` records the discovery-first census design that preceded the current nationwide readiness/execution layer.
- `central_directory_exposure_classification.md` records a particular expansion classification and is not a complete statement of current state coverage.

## State-specific technical investigations

Files prefixed `mi_`, `oh_`, and `me_`, plus related Ohio/Maine notes, are technical case studies from the early portability work. Their platform observations, reporting-topology lessons, and extraction findings remain useful, but their cohort sizes and “next target” language are historical snapshots rather than the current national roadmap.

Current coverage/readiness claims should come from registries and reproducible audit outputs, not from old case-study prose.

## Status vocabulary

Use these terms precisely:

- **catalogued/discovered** — a candidate source/surface is known.
- **verified** — provenance/official status has been affirmatively checked.
- **fetchable** — bytes were successfully acquired in the relevant run.
- **parser selected** — a supported parser/artifact path has been identified.
- **parsed** — structured records were produced.
- **normalized** — canonical observations were produced.
- **replay tested** — preserved evidence can be reprocessed successfully.
- **refresh verified** — repeated election-night updates have been observed/validated.

Never substitute one of these for another.
