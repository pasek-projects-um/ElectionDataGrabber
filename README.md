# ElectionDataGrabber

ElectionDataGrabber is a national, auditable pipeline for discovering, snapshotting, classifying, normalizing, replaying, and reconciling U.S. election-result sources.

Michigan was the initial test bed; it is no longer the project boundary. The repository now maintains a breadth-first result-surface catalog for all 50 states plus DC, geography-first source-evidence ledgers, nationwide harvested-source verification/fingerprint workflows, and reusable execution paths for multiple structured/tabular/document platform families.

## Current system shape

The acquisition pipeline is deliberately staged:

1. **Discover/catalog** official or plausibly official result surfaces and preserve provenance.
2. **Verify/fetch** without converting network failures into source-absence claims.
3. **Fingerprint** platform/report families and discover downloadable/API artifacts.
4. **Select/execute adapters** only when the parser contract is actually supported.
5. **Normalize** into canonical election, jurisdiction, reporting-regime, reporting-unit, contest/choice, vote-mode, and observation models.
6. **Persist immutable snapshots** and bind normalized facts to snapshot hashes.
7. **Replay/test** adapters against preserved evidence.
8. **Reconcile** geography, reporting topology, overlapping sources, and historical identity explicitly rather than assuming arithmetic additivity.

Catalog breadth, executable ingestion, normalized coverage, replay coverage, and election-night refresh verification are separate metrics.

## Coverage and source topology

`registry/first_pass_state_result_surfaces.csv` contains at least one catalogued result surface for every state plus DC. This is a discovery/breadth milestone, **not** a claim that every local election authority or reporting unit is fully ingested.

Within states, the project tracks expected primary election geographies/authorities separately from source leads. A geography can have multiple credible outlets; one source can cover many geographies. State mirrors, local election-night dashboards, certified files, APIs, and historical archives are retained as distinct evidence when they provide different operational value.

External repositories such as MEDSL, OpenElections, research collections, and source-specific scraper projects are used for discovery, provenance reconstruction, historical QA, and endpoint intelligence. They are not silently promoted to authoritative result feeds when the underlying official artifact is unknown.

## Execution families

Reusable support includes generic CSV, Excel, JSON, HTML/document/PDF paths plus platform/report-family work such as Clarity/ENR, Enhanced Voting, CivicPlus discovery, Ohio standardized BOE/report families, structured-web artifact discovery, and vendor-oriented Scytl/Electionware discovery. The readiness pipeline routes harvested sources to existing adapters, structured artifact discovery, platform follow-up, new-adapter work, or explicit fetch-blocked status.

A URL that merely looks like a results portal is not considered executable. Parser promotion requires an actual supported runtime path.

## Core invariants

- Prefer official structured data over rendered pages when available.
- Save immutable raw snapshots before normalization.
- Keep source timestamps and fetch timestamps separately.
- Treat jurisdiction, election authority, reporting regime, reporting unit, and source as separate identities.
- Treat precinct/reporting-unit identity as election/regime-specific until a provenance-bearing crosswalk establishes continuity.
- Preserve vote-mode detail and raw source labels.
- Never infer arithmetic additivity from geographic containment.
- Preserve non-geographic and centrally reported absentee/mail/special units instead of forcing them into precinct sums.
- Preserve multiple source outlets and calibrate overlap empirically; source similarity can establish redundancy but dissimilarity alone does not establish independence.
- Never promote result/display order to voter-facing ballot order without authoritative ballot evidence.
- Never interpret crawl/fetch/parser failure as evidence that a source does not exist.

## Repository map

```text
registry/                       canonical registries, source catalogs, denominators
audit/                          generated evidence/readiness outputs and checked-in audit inputs
scripts/                        discovery, census, promotion, execution, probe, and audit utilities
src/election_data_grabber/
  adapters/                     reusable source/platform/report-family adapters
  canonical_ids.py              jurisdiction/authority identity helpers
  geography_hierarchy.py        non-additive geography relationships
  reporting_*                   reporting-regime/unit identity and topology
  source_overlap*.py            source snapshot overlap calibration/persistence
  supported_execution.py        executable parser/replay boundary
docs/                           architecture contracts and historical technical investigations
```

## Historical pilots

Michigan, Ohio, Maine, Connecticut, and Pennsylvania supplied early stress tests for live reporting, county/municipality authority models, standardized reports, micro-geography, temporal geography, and source portability. Their detailed docs remain useful case studies, but they should not be read as the current national coverage boundary.

## What comes next

The current priority is depth rather than another breadth-only catalog pass: convert harvested source candidates into verified executable feeds, implement the highest-leverage remaining platform families, deepen within-state authority/geography coverage, verify election-night refresh behavior, and preserve replayable evidence for each promotion.

See `ROADMAP.md` for the current work program and `registry/README.md` for the distinction between catalog, evidence, and executable coverage.
