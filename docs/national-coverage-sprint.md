# National starting-point coverage sprint

Tracking issue: https://github.com/pasek-projects-um/ElectionDataGrabber/issues/67

**Only active feature goal:** enumerate every election-administration/reporting unit in the United States and supply at least one credible discovery starting URL per unit. Preserve alternative URLs when jurisdiction ownership is ambiguous.

Do **not** count the existing 757-unit registry as the full national denominator. Never count a state-directory fallback as a verified local official site. Keep separate coverage metrics for any-start, direct/shared source and verified reachable.

Work state by state, reconciling jurisdiction identifiers, authoritative parent relationships, and source provenance. Keep URL inventory CI deterministic and fast; use manual crawls for evidence gathering. Defer local model classification, deployment, additional ingestion adapters and unrelated features until the nationwide any-start metric genuinely reaches 100%.

## Internet Archive escalation for uncertain starts

When a jurisdiction has only a state-directory fallback, generic government homepage,
unreachable or ambiguous election-office page, or multiple competing candidate URLs,
search the Wayback Machine for its election-site link structure. Restrict queries to
the 2024 November 5 general election window, jurisdiction-specific 2025 election dates,
and jurisdiction-specific 2026 primary dates. Dates must be supplied explicitly; never
assume every jurisdiction has the same 2025 election or 2026 primary date.

Use `scripts/wayback_starting_point_leads.py --targets targets.csv` with columns
`jurisdiction_id,seed_url,election_type,election_date`. The script produces archived-only
candidate links and their snapshot timestamps, and is deliberately **manual**, not PR CI.
Archive evidence must not be treated as proof of current reachability or official status.
Promote an archive lead to a verified current start only after a separate live check and
authority/jurisdiction confirmation. Record original and archived URLs together.

Prioritize these archive lookups over speculative general web searching for uncertain units.


## High-yield coverage pass (October 2026)

**Prioritization correction:** finish straightforward election-authority units and their starting URLs before tackling large, fragmented municipal/town topologies. The near-term priority is high-confidence coverage of consequential election reporting jurisdictions, not maximum raw unit count. This is prioritization, **not** a redefinition of the nationwide denominator or a claim of 100% coverage.

First clear small and tractable remaining gaps: DC (1), AK (1, state-administered model), HI (4), RI (39), and MN (87), then tackle IL (108) and MO (116) by enumerating their separate election authorities. Where possible, reuse official state directories and retain distinct source URLs/provenance. Avoid treating Census geography as automatically equivalent to an election-administration authority.

Defer the most fragmented rosters from this **pass**: NH (234), VT (247), MA (351), WI (1,850). They remain active gaps, not covered by assumption or removed from the denominator. Revisit based on available bandwidth and election competitiveness/contested district relevance; do not claim every election in a state is uncompetitive.

Repair shared-core derived-tracker consistency and restore passing CI before merging expansion. Run Wayback date-bounded lookups only for ambiguous links in the states currently being addressed. Report newly named units, direct verified leads, fallback-only units, provisional-denominator status, and explicitly deferred gaps separately.

## Two complementary coverage weights (October 2026)

Raw jurisdiction counts are a diagnostic, **not** a uniform unit of public value. Publish **three parallel measures**: (a) jurisdiction enumeration/source coverage, (b) population-weighted coverage, and (c) unique reporting-place-weighted coverage. Do not collapse these into a single opaque score.

**Population weight.** Prefer the most relevant Census population estimate for the geography **actually covered by the source**, with vintage and Census GEOID recorded. For election participation analysis use voting-age / citizen voting-age population where credible and available; otherwise clearly label total resident population as the proxy. Calculate covered population as the distinct union of covered geographic units, not the sum of overlapping state, county, municipal, and precinct authorities. An official statewide source may cover many counties, but only to the extent it actually publishes the relevant results at the requested granularity. Store estimates separately from confirmed source reachability and report missing population weights explicitly.

**Unique reporting-place weight.** Estimate the number of **distinct units expected to report results**: precincts, wards, municipalities, county reporting units, or other locality-specific election-night result partitions. Define a stable reporting-unit identity per election, jurisdiction, and unit type; deduplicate units exposed by county, state, or vendor mirror feeds. Separate (1) expected units based on prior elections / official reporting-unit inventories, (2) units whose results are present in the source, and (3) units with a verified current live endpoint. The expected unit count is a provisional estimate, **not** equal to the number of election authorities. Don't infer an equal count per county or municipality.

For both weights: publish covered numerator, known denominator, unknown/unallocated weight, evidence link, estimate date/vintage, granularity and confidence. Give direct and fallback-only coverage separate metrics. A generic state authority URL is *not* population- or reporting-place-covered unless the actual results coverage has been demonstrated. Do not assign phantom population or reporting units to unresolved geography.

**Prioritization:** favor work that adds the most currently uncovered people and/or unique election-night reporting points per unit of discovery effort. Keep these as two views and use a Pareto frontier when they disagree. Contest competitiveness, congressional/senatorial relevance and election-night timeliness are optional separate priority flags, not ingredients silently baked into either coverage weight. Preserve tractable-first execution while avoiding a simplistic assumption that every county or town is equally consequential.

**Implementation acceptance criteria:** establish a versioned geographic weight input and provenance, deterministic allocation with explicit overlap/deduplication handling, automated per-state/national weighted coverage outputs, tests for nested state-county-municipality sources and unknown weights, and explicit disclaimers against interpreting starting-URL presence as actual results coverage. This is a proposed measurement model until population/reporting-place inputs and verified source mappings are populated.


### Granularity-aware reporting visibility

Expected reporting-unit counts and **observable** reporting-unit counts must be distinct. A small city may publish results at individual precinct level while a much larger county publishes only county-wide, municipality-wide, or aggregated precinct-group totals. Geographic size, population, and administrator count do not determine publication granularity; do not presume that a larger county exposes more distinct reporting units.

For each source/election, record the finest actually observed geographic reporting level (`precinct`, `ward`, `municipality`, `county`, `state`, `mixed`, or `unknown`), the number of distinct observed units at that level, the expected finer-grained unit count if known, and provenance. A source with only a county total covers the county's people for geographic-total accessibility but **does not cover** its constituent precincts for precinct-level accessibility. Avoid converting one county aggregate into hundreds of inferred precinct rows or assigning an unsupported precinct denominator. Mixed-level feeds require explicit child/parent relationships and deduplication before counting observable geographic units.

Report reporting-place coverage at **several resolution thresholds**, at minimum any geographic result, municipality-or-finer, and precinct-or-finer. Keep unknown or aggregated-only sources separate rather than scoring them as zero population coverage or full precinct coverage. When prioritizing source discovery, measure the likely *incremental visibility* a source adds at each resolution, not just the number of nominal precincts in its geography. It is plausible, not established as a universal rule, that smaller jurisdictions expose finer local geography more often than large aggregations; empirical source evidence overrides that heuristic.


### Blended prioritization objective

Prioritize incremental gains in **both** distinct population covered and unique observable geographic reporting units. Neither dimension should be treated as optional or used exclusively. As a provisional working model, score a candidate source by `0.5 * normalized_incremental_population_coverage + 0.5 * normalized_incremental_reporting_unit_coverage`, where each incremental coverage gain is divided by the corresponding *national* independently estimated denominator and deduplicated against already covered geography/units at the observed resolution. An equal split is an initial tunable planning parameter, **not** a validated empirical coefficient. Show component gains side by side and permit sensitivity checks at 40/60 and 60/40. Never rank using raw counts on incomparable scales.

Where discovery cost estimates are meaningful, use blended incremental benefit per estimated effort as the ordering heuristic; retain the ability to favor a strategically critical Congressional/Senate election source separately without altering the two underlying coverage measures. Unknown population or reporting-unit estimates must be shown explicitly (with uncertainty ranges when possible), not silently assigned zero or fabricated. A countywide total can materially increase population coverage while adding just one observable reporting aggregation; precinct-level municipal results can add substantial distinct reporting units even with less population. Count only **new** population and reporting detail relative to existing sources; state/county/vendor overlap must not inflate scores. Preserve separate any-results, municipality-or-finer, and precinct-or-finer reporting-resolution metrics.


### Provisional unknown-granularity proxy: cube root of population

When the number of *observable* geographic result-reporting units is unknown but an attributable population estimate exists, use the heuristic **estimated reporting units = population^(1/3)**, rounding to the nearest positive whole number for nonzero populations. Population is measured in **persons**; this scaling and its coefficient of 1 are planning assumptions, not an empirically validated forecast. Example values: 1,000 people → ~10 units; 8,000 → ~20; 125,000 → ~50; 1,000,000 → ~100. Use the same definition and vintage of population across comparisons.

This proxy affects **estimated** reporting-unit-weighted prioritization only. Always take actual observed precinct/ward/municipal counts when available, and retain expected units derived from official rolls separately. Tag any imputed count as `population_cube_root_proxy`; preserve the source population and population vintage, distinguish it from verified observations and from the number of administrative jurisdictions, and use an uncertainty flag. Where population is absent, mark the estimate unknown—do not silently substitute zero. Never mark inferred units as actually covered, verified precincts, or confirmed election-night feeds. Deduplicate overlapping geographies before aggregating weighted benefits. A source with only a countywide total still has one **observed** county-level reporting aggregation regardless of this estimated finer-unit proxy. Apply the proxy only within a comparable granularity frame and avoid counting the same underlying geography twice.
