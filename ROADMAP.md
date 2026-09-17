# ElectionDataGrabber Roadmap

**Status:** living project roadmap  
**Last substantive refresh:** 2026-09-17  
**Update rule:** revise this document whenever a milestone is completed, a material discovery changes priorities, or a new workstream is opened. Keep completed work for provenance rather than silently deleting it.

## North star

Build a national, auditable system for historical/final and election-night election-result acquisition at the most granular official reporting level available, while preserving source provenance, reporting topology, temporal geography, candidate/ballot-line semantics, and uncertainty.

The scaling objective is **parser/platform families rather than locality-specific code**.

## Current position

### Completed / consolidated on main

- [x] Canonical source, snapshot, reporting-unit, contest-choice, ballot-summary, and result-observation models.
- [x] Immutable SHA-256 snapshot/provenance layer and respectful fetch base.
- [x] Generic CSV, HTML, document inventory, discovery, and PDF extraction layers.
- [x] Michigan county census and election-night architecture.
- [x] Washtenaw live ingestion, reconciliation, diffing, and persistence.
- [x] Ohio 88-county portability census and reusable precinct-detail family.
- [x] Maine municipality-first authority/discovery and artifact-audit architecture.
- [x] Connecticut 169-town statewide registry and historical-geography policy.
- [x] Pennsylvania 67-county registry and state-bulk-first strategy.
- [x] National source-census foundation and cross-state semantic edge cases.
- [x] Explicit distinction between source/display order and authoritative ballot order.
- [x] Explicit distinction between election-night reporting topology and certified/final geography.

### Active: PR #11 — national state authority expansion

Latest successful census: **24 states / 911 discovery observations**.

Central repositories currently classified as directly exposing useful local infrastructure:
AZ, HI, IA, KY, MD, MO, NH, NJ, OR, VA.

MN is currently indirect.

Generic central-directory extraction remains unresolved for:
AK, AL, GA, KS, LA, MA, ND, NM, NY, RI, SC, VT, WI.

These are directory-enumeration problems, not evidence that local result sources do not exist.

## Coverage accounting

The national coverage tracker uses mutually exclusive locality capability states:

1. **final_only** — historical/final/certified source established; election-night source not established.
2. **election_night_only** — election-night source established; durable historical/final source not established.
3. **both** — both capabilities established.
4. **known_missing_source** — locality is canonically known and investigated, but neither useful source class is established.
5. **estimated_unknown** — expected primary units not yet individually enumerated/adjudicated.

Derived metrics:

- final coverage = final_only + both
- election-night coverage = election_night_only + both
- any-source coverage = final_only + election_night_only + both

Planning invariant:

`expected_primary_units = final_only + election_night_only + both + known_missing_source + estimated_unknown`

**Known issue:** the current tracker has not yet reconciled discovery observations to canonical jurisdiction IDs and presently double-populates missing/unknown denominators. Do not treat its current capability counts as national coverage statistics.

Current seeded planning denominator: approximately **4,054 primary local units across 24 states**. This is provisional and should be replaced state-by-state with authoritative enumeration.

## Immediate milestone: make coverage real

- [x] Define stable canonical jurisdiction/authority IDs. See `src/election_data_grabber/canonical_ids.py` and `docs/canonical_jurisdiction_identity.md`.
- [ ] Repair tracker invariant and distinguish enumerated-but-unresolved from genuinely unknown units.
- [ ] Reconcile PR #11's 911 discovery observations to canonical jurisdictions.
- [ ] Classify each reconciled locality as final_only / election_night_only / both / known_missing_source.
- [ ] Add evidence/provenance fields for every capability assignment.
- [ ] Produce state and national scorecards: expected, enumerated, final-capable, election-night-capable, both, missing, unknown.
- [ ] Add automated invariant tests so tracker arithmetic cannot regress.
- [ ] Merge PR #11 after reconciliation and CI are green.

## Next milestone: finish authority enumeration

Work unresolved states alphabetically with state-specific central-directory profiles rather than bespoke result parsers:

- [ ] Alaska
- [ ] Alabama
- [ ] Georgia
- [ ] Kansas
- [ ] Louisiana
- [ ] Massachusetts
- [ ] North Dakota
- [ ] New Mexico
- [ ] New York
- [ ] Rhode Island
- [ ] South Carolina
- [ ] Vermont
- [ ] Wisconsin

For each state, record:
- authoritative expected unit count and authority model;
- units individually identified;
- local authority URLs exposed;
- result-site URLs exposed;
- directory mechanism (anchors, table, cards, search widget, API, scripts, state-only);
- historical/final capability;
- election-night capability;
- smallest observed reporting unit;
- confidence and evidence.

## Platform leverage milestone

Once canonical jurisdictions are attached to discoveries:

- [ ] Build a national platform/report-family census by number of authorities unlocked.
- [ ] Prioritize reusable families by locality coverage and election-night value.
- [ ] Complete normalized parsers where discovery/profile support exists but normalization does not.
- [ ] Highest-value known families include Enhanced Voting, Clarity ENR, standardized tabulator/SOV/canvass reports, CivicPlus-as-discovery, Electionware, and recurring static document families.
- [ ] Track the target metric: **new locality-specific parser code should trend toward zero**.

## State-specific technical debt / follow-up

### Maine
- [ ] Add proper post-shard aggregation for pending-source triage.
- [ ] Continue authority/source discovery; current dominant blocker is discovery, not parser failure.
- [ ] Keep image-only/OCR-required artifacts provisional E until validated and reconciled.

### Michigan
- [ ] Complete normalized table-to-ResultObservation parser for standardized SOV/canvass reports.
- [ ] Deepen unknown-web family classification.
- [ ] Preserve election-night resolution independently from certified resolution.

### Ohio
- [ ] Convert family-classified A cases into artifact-executed production evidence where still needed.

### Connecticut
- [ ] Expand voting-district recovery while preserving historical 8-county vs current planning-region geography.

### Pennsylvania
- [ ] Finish full 67-county platform/capability classification.

## Data-model guardrails

Maintain these invariants throughout expansion:

- Reporting topology is separate from final/certified geography.
- Temporal geography/crosswalks are explicit.
- Vote mode is recorded only when explicit or defensibly derived.
- Candidate identity, candidacy, ballot line, party label, and ballot position are separate concepts.
- Source/display order is never promoted to voter-facing ballot order without authoritative evidence.
- Fusion voting preserves ballot-line votes and candidate-combined totals.
- Election stages/runoffs preserve stable candidacy identity and stage semantics.
- Missing registration denominators remain null/not-applicable where the jurisdiction has no registration system.
- Ballot-delivery regime is separate from reporting-mode breakout.
- Source disagreement is retained and adjudicated, never silently conformed.

## Modeling and assurance — after acquisition coverage matures

- [ ] Separate turnout and preference: electorate composition × turnout × candidate preference.
- [ ] Add uniform-by-group swing benchmarks.
- [ ] Add hierarchical / empirical-Bayes models by administrative and reporting regime.
- [ ] Historical replay/backtesting.
- [ ] Administrative-regime tables and temporal-geography-aware comparisons.
- [ ] Neutral anomaly detection plus affirmative assurance/accounting checks.
- [ ] Preserve uncertainty and avoid treating ecological inference as individually identified behavior.

## Roadmap maintenance protocol

At the end of any material work session:

1. Mark completed checklist items.
2. Update the current-position metrics from actual artifacts/workflows.
3. Record newly discovered blockers under the relevant milestone.
4. Reorder only when evidence changes expected leverage.
5. Add links/PR numbers or artifact paths for major deliverables.
6. Keep provisional estimates explicitly labeled.
7. Never convert crawl failures into substantive source-absence claims.
8. Update the roadmap in the same PR as the work whenever practical.

The roadmap is the project's canonical statement of **where we are, what is next, and why**. Detailed registries and audit artifacts remain the source of truth for individual jurisdictions.
