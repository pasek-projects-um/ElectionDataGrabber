# ElectionDataGrabber Roadmap

**Status:** living project roadmap  
**Last substantive refresh:** 2026-10-21

## North star

Build a national, auditable system for historical/final and election-night result acquisition at the most granular official reporting level available, while preserving source provenance, reporting topology, temporal geography, candidate/ballot-line semantics, source overlap, and uncertainty.

Scale by **platform/report family and source topology**, not one scraper per locality.

## Current position

### National breadth is established

- [x] At least one first-pass result surface catalogued for all 50 states plus DC.
- [x] Geography-first source-evidence ledger and unresolved-search queue.
- [x] Canonical locality/authority identity separated from source URLs and reporting-unit identity.
- [x] External lead provenance for MEDSL, ElectProject/McDonald, NYT precinct-source research, and DownBallotR-style scraper intelligence.
- [x] Cross-corpus gap accounting that requires a concrete primary-source candidate for every state/DC when combined with the vetted internal state-surface catalog.
- [x] Harvested-source execution queue, fetchability/platform probes, and readiness routing.

The 51-jurisdiction catalog is a **breadth milestone, not a completeness claim**. It does not mean every county, municipality, election authority, reporting unit, or election-night feed within each state has been enumerated or normalized.

### Execution maturity is now explicit

The system distinguishes:

`discovered → fetchable → parser_selected → parsed → normalized → replay_tested`

Artifact discovery can advance a source to a parser-selected/fetch-next state without pretending the artifact has already been parsed. Generated readiness outputs separately route sources toward existing adapters, artifact discovery, platform follow-up, new-adapter work, or fetch-blocked investigation.

Current reusable paths include generic CSV/Excel/JSON and document/HTML/PDF handling; Clarity landing-page/detail discovery and XML execution; Enhanced Voting; structured-web artifact ranking; vendor-oriented Scytl/Electionware discovery; Ohio standardized report families; and other state/source-specific adapters already present in the package.

### Coverage accounting is geography-first

Keep these dimensions separate:

1. expected/enumerated primary election geographies or authorities;
2. candidate source leads;
3. positively adjudicated final/election-night capabilities;
4. execution maturity;
5. normalized/replay-tested coverage;
6. election-night refresh verification.

A locality can have multiple sources without increasing the denominator. A source can cover multiple localities. Geographic containment does not imply arithmetic additivity.

Negative findings require affirmative adjudication. HTTP failures, robots restrictions, parser failures, or missing links remain unresolved evidence—not `known_missing_source`.

## Completed architecture foundations

- [x] Immutable snapshot/provenance layer.
- [x] Canonical jurisdiction and independent authority identities.
- [x] Reporting-regime and election-specific reporting-unit identity.
- [x] Temporal identity aliases/crosswalks.
- [x] Governed vote-mode semantics with raw-label preservation.
- [x] Source/display order separated from authoritative ballot order.
- [x] Election-night reporting topology separated from certified/final geography.
- [x] Non-additive geography relationships and explicit central absentee/mail/special reporting units.
- [x] Source-overlap calibration model with the guardrail that similarity can establish redundancy but dissimilarity alone cannot establish residual independence.
- [x] Snapshot/calibration persistence and external-source-lead provenance.
- [x] Nationwide source harvesting/readiness pipeline.
- [x] Readiness-to-adapter compatibility bridge and structured artifact routing.

## Current milestone: turn breadth into executable depth

The next work should be driven by generated readiness/evidence, not by another undifferentiated web crawl.

October 10 discovery-layer continuation: `scripts/build_national_layer_frontier.py`
now joins named units, direct/state-fallback starts, and exact observed page provenance
into separate national/state/unit/source queues. The current registry has 6,288 named
units, 191 with direct starts and 6,097 using state fallbacks; 46 state denominators
remain provisional. Prioritize national authority-directory resolution and linked
local websites before concentrating on individual historical payloads. See
`docs/national-layer-frontier.md`; these offline queues do not establish new coverage.

The repeatable discovery watcher now provides persistent due-page scheduling,
bounded/robots-aware requests, immutable captured HTML, changed/new-link events,
retained historical leads, depth-bounded HTML follow-up and a candidate inspection
queue. Scheduler deployment, national throughput measurement and vote-payload
activation remain outstanding; see `docs/national-monitoring-setup.md`.

Directory-layer continuation: registered state directory/authority captures now
produce a separate local-authority link review queue with exact observed URLs,
state-scoped unit-label matching, ambiguity, provenance and unresolved unit IDs.
This is candidate extraction, not adjudicated new local coverage. See
`docs/authority-directory-frontier.md` for the official-capture evidence pass.

- [ ] Execute and replay every harvested candidate already covered by an existing adapter family.
- [ ] Fetch discovered JSON/XML/CSV/Excel artifacts and promote successful cases through normalization/replay.
- [ ] Rank remaining platform families by number of jurisdictions/authorities unlocked and election-night value.
- [ ] Implement high-leverage missing platform adapters in batches.
- [ ] Deepen within-state authority/geography enumeration using canonical denominator sources.
- [ ] Separate enumerated primary units, units with any lead, and unreconciled candidate URLs in depth metrics.
- [ ] Verify repeated election-night refresh behavior: stable race/unit identity, cumulative revisions, timestamps, and throughput.
- [ ] Persist synchronized source snapshots and matched-pair overlap evidence for feeds that may be mirrors/partial overlaps.

## November 2026 operational readiness (October 21)

- [x] Repair and production-check bounded discovery execution (PR #77; two successful
  runs, latest 40 pages / 54 requests in 223.1 seconds, approximately 6.07 MB artifact).
- [x] Add an explicit-feed collector CLI with atomic SQLite checkpoints, immutable
  raw/sample captures, conditional polling, offline replay and integrity/staleness status.
- [x] Exercise restart, changed totals, corrections, row removal, network failures,
  robots/redirect budgets, empty manifests and artifact corruption in deterministic CI.
- [x] Rehearse the production Washtenaw August 2026 HTML, fixing real contest headings
  and replacing the hardcoded election ID with explicit configured identity.
- [ ] Adjudicate and enable actual November election-specific payloads. The November
  manifest is empty; the August rehearsal is historical evidence only.
- [ ] Deploy the persistent collection worker, backup and supervisor health monitoring.
- [ ] Verify actual November updates/latency, source timestamps, corrections, topology
  and mirror overlap. No automatic refresh-verification promotion is implemented.

`election-grab readiness` publishes separate national discovery/candidate/capability
counts and selected-feed execution health, with input hashes. Weighted population and
reporting-place coverage remain explicitly unknown. See `docs/election-night-runbook.md`.

## Source-overlap and redundancy milestone

Multiple outlets for the same reporting geography are useful redundancy, not automatically duplicates to delete.

- [x] Preserve source outlet separately from geography and underlying artifact/feed.
- [x] Compare synchronized snapshots at comparable reporting progress.
- [x] Preserve reporting-unit and vote-mode overlap evidence.
- [x] Require explicit residual-independence evidence before treating two feeds as independent observations.
- [ ] Add reporting-basis compatibility to snapshot matching.
- [ ] Prevent many-to-one snapshot matching where it biases calibration.
- [ ] Add temporal lead/lag diagnostics and conservative zero-vector handling.
- [ ] Emit durable pair-level match audit artifacts alongside summary calibrations.

## Within-state depth milestone

The project must not equate one statewide surface with full state coverage.

For each state, maintain evidence for:

- authoritative expected unit count and authority model;
- individually enumerated units;
- units with final and/or election-night source capability;
- all credible source outlets per unit;
- smallest observed reporting unit;
- platform/report family;
- execution maturity and replay status;
- explicit unresolved and affirmatively missing cases.

Prefer states/localities with high election-night value and relevant federal/state contests once easy/high-leverage families have been exhausted, while recognizing that complete coverage of every difficult low-value source may not be operationally worthwhile.

## Historical state work

Michigan, Ohio, Maine, Connecticut, and Pennsylvania remain important architecture case studies. Their state-specific docs describe the investigation at the time and should be read as technical evidence, not as the current project boundary.

Remaining state-specific follow-up should be prioritized through the national readiness/depth matrices rather than maintained as a separate five-state roadmap.

## Modeling and assurance — after acquisition depth matures

- [ ] Separate turnout and preference: electorate composition × turnout × candidate preference.
- [ ] Add uniform-by-group descriptive benchmarks.
- [ ] Add hierarchical / empirical-Bayes models with administrative/reporting-regime-aware pooling.
- [ ] Historical replay/backtesting.
- [ ] Neutral anomaly detection plus affirmative assurance/accounting checks.
- [ ] Preserve uncertainty and avoid treating ecological inference as individually identified behavior.

## Roadmap maintenance protocol

At the end of material work:

1. Update this file from merged artifacts/workflows, not remembered counts.
2. Keep catalog, capability, execution, normalized, replay, and refresh coverage distinct.
3. Record newly discovered blockers under the relevant milestone.
4. Keep historical investigations but label them as snapshots when their status language ages.
5. Never convert crawl/fetch/parser failures into source-absence claims.
6. Update documentation in the same PR as architecture/maturity changes whenever practical.

Detailed registries and generated audit artifacts remain the source of truth for individual jurisdictions and source candidates.
