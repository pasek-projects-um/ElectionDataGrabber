# Geographic source-evidence ledger

Coverage depth is geography-first. The project now has a first-pass state/DC result-surface catalog, but a state-level surface is not evidence that every reporting authority, county, municipality, parish, town, ward, or precinct family has been discovered.

## Unit ledger

Maintain one row per expected primary election geography/authority with:

- canonical `jurisdiction_id`, state, level, canonical name, external/FIPS/GEOID where available;
- independent `authority_id` where the election authority is not identical to the geography;
- denominator provenance and effective dates;
- final-result capability and election-night capability as separate adjudications;
- every candidate source lead, not only the selected source;
- search/test timestamps and explicit unresolved/missing status.

A negative finding is evidence only after affirmative adjudication. Crawl failure, 403, robots denial, or a missing link must remain unresolved rather than becoming `known_missing_source`.

## Source-lead ledger

Each geography may have many leads. Store at minimum:

`jurisdiction_id, authority_id, lead_url, lead_origin, origin_locator, source_scope, family_hint, official_status, discovered_at, last_tested_at, fetch_status, artifact_type, parser, execution_stage, snapshot_sha256, notes`.

`lead_origin` should distinguish:
- official directory/search;
- official result/archive page;
- search-engine discovery;
- external GitHub/research archive;
- historical snapshot/archive;
- manually supplied lead.

External repositories are discovery and validation evidence, not authoritative result sources unless they preserve and identify the underlying official artifact.

## Discovery loop

For every enumerated geography, generate searches from canonical name + state + election terms and known authority names. Search both the open web and reusable archives/code repositories. Feed newly discovered URLs back into the source-lead ledger, fingerprint them, fetch respectfully, identify downloadable artifacts/API endpoints, and run the appropriate parser where one exists.

The loop is complete for a geography only when we can say which of these is true with evidence:
1. official statewide source covers it;
2. official local source covers it;
3. both exist;
4. leads exist but remain unverified/unparseable;
5. affirmatively investigated and no useful source has been established.

## External lead catalogs

Useful national/cross-state lead sources include MIT Election Data + Science Lab official-return repositories, projects that preserve source-specific scrapers, and national precinct compilations. These are especially valuable for reconstructing old official URLs, identifying platform families, discovering hidden API/download endpoints, and checking expected geography names.

Initial GitHub lead catalogs to audit:
- MEDSL/2024-elections-official (and analogous 2022/2020/2018 repositories);
- gchickering21/DownBallotR, whose state-specific scrapers document several official backends;
- nytimes/presidential-precinct-map-2024 for state-by-state precinct coverage/caveats;
- locality-specific archival scrapers such as rdmurphy/scrape-la-county-election-results-2026;
- existing project-specific scrapers when they expose historical endpoint patterns.

Do not ingest third-party vote totals merely because they are easier to obtain. Prefer them as a map to the primary source and as an independent reconciliation check.

## Completeness metrics

Report separate rates for:
- geography enumeration;
- geography with >=1 source lead;
- geography with verified official source;
- geography with fetchable artifact;
- geography with normalized observations;
- geography replay-tested;
- election-night geography with refresh semantics verified.

Never collapse these into a single national coverage percentage.
