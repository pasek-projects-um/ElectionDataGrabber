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

When the number of *observable* geographic result-reporting units is unknown but an attributable population estimate exists, use the heuristic **estimated reporting units = population^(1/3) / 10**, rounding to the nearest whole number, with a minimum of 1 for positive populations. Population is measured in **persons**; this scaling and its coefficient of 1 are planning assumptions, not an empirically validated forecast. Example values: 1,000 people → ~1 unit; 8,000 → ~2; 125,000 → ~5; 1,000,000 → ~10. Use the same definition and vintage of population across comparisons.

This proxy affects **estimated** reporting-unit-weighted prioritization only. Always take actual observed precinct/ward/municipal counts when available, and retain expected units derived from official rolls separately. Tag any imputed count as `population_cube_root_proxy`; preserve the source population and population vintage, distinguish it from verified observations and from the number of administrative jurisdictions, and use an uncertainty flag. Where population is absent, mark the estimate unknown—do not silently substitute zero. Never mark inferred units as actually covered, verified precincts, or confirmed election-night feeds. Deduplicate overlapping geographies before aggregating weighted benefits. A source with only a countywide total still has one **observed** county-level reporting aggregation regardless of this estimated finer-unit proxy. Apply the proxy only within a comparable granularity frame and avoid counting the same underlying geography twice.


### Candidate replacement for the cube-root proxy (October 2026)

The simple cube-root/10 proxy likely grows too slowly at scale and is not anchored to precinct-size intuition. A **proposed, uncalibrated** visibility model is `R(P) = max(1, round((P/1000) * min(0.8, 0.20*(P/10000)^0.2)))` for positive population P in persons. This separates potential precinct-sized units (`P/1000`) from the hypothesized share visibly reported (`q(P)`), which increases mildly with population but is capped. This is *not* evidence that larger jurisdictions actually publish more detail; large-county aggregation can invert that expectation, so actual source observed granularity must override estimates. Record the proxy formula, parameters, confidence and provenance; do not conflate predicted visibility with verified reporting units. Calibrate on known 2024/2025 and 2026 primary source examples before adopting the model in production or substituting it for the currently documented cube-root/10 baseline. Report both population and unique observable reporting-unit coverage independently in the blended score.


### Heteroskedastic high-population visibility: revised candidate model

The previously proposed increasing-visibility-fraction power law is **too optimistic at high population** and should not be used as the central estimate. Replace that candidate with a **sublinear, saturating typical-case** reporting-unit estimate (for positive population (P) in persons):

`typical(P) = max(1, round(2 * (P / 10000)^0.55))`.

This is a provisional planning assumption, not measured precinct visibility. Example typical values: 10,000 → 2; 100,000 → 7; 1,000,000 → 25; 10,000,000 → 89. The actual number may be far lower (a single countywide aggregate) or much higher (hundreds/thousands of published precincts). Accordingly **do not treat typical(P) as a deterministic prediction**. Model uncertainty explicitly, increasing with size: define `s(P) = 0.35 + 0.20 * max(0, log10(P/10000))` (for positive P), and provisional planning bounds `lower(P) = max(1, round(typical(P) * exp(-1.645*s(P))))`, `upper(P) = max(typical(P), round(typical(P) * exp(1.645*s(P))))`. These are **scenario bands, not calibrated 90% statistical confidence intervals**; empirical residuals must be used to calibrate them.

A large county showing only aggregate results remains a realistic lower-tail outcome, regardless of population. Keep a separate coarse-aggregation scenario (1 or a handful of geographic result rows) in prioritization and report high-population estimates as a range rather than a precise number. Use source- or state-specific publication models once sufficient historical results are observed; a simple overall population function cannot explain mixed vendor / reporting policies. Where observed unit counts exist, use those rather than any imputation.

Keep population coverage distinct from geographic-detail coverage and deduplicate across overlapping feeds. For ranking candidates with unknown granularity, retain a transparent conservative typical benefit and sensitivity to lower-/upper-visibility scenarios. Neither imputed unit counts nor scenario bands count as observed geographic reporting units.

This proposal supersedes the prior **increasing-visibility-fraction** candidate for prioritization review; retain the original cube-root/10 assumption only as historical context, not as a second active default. No scoring-pipeline implementation or empirical calibration is claimed yet.


## Current tactical target: all except three largest unresolved state rosters

Target **every state/DC other than Wisconsin (1,850 nominal missing), Massachusetts (351), and Vermont (247)** for this pass. Do **not** defer New Hampshire (234): its municipal/town and ward units are now in scope. From the October 9 tracker, the eight in-scope states/DC still needing names are NH 234, MO 116, IL 108, MN 87, RI 39, HI 4, AK 1, DC 1 (590 total). Other states have already met their provisional enumeration counts. Address these eight using official jurisdiction rosters; preserve each roster's unit model, IDs, provenance and true overlap. Do not fake coverage by assigning state links as locally verified sources or by silently truncating municipalities. Hawaii county-equivalents now fall within the existing Census enumerator. Continue to report weighted actual source coverage separately from named enumeration. The 2,448 units in the three deferred states remain visible gaps; this is a near-term sprint scope, not a revision of national completeness criteria.


## Eight-state roster ingestion completed — October 9, 2026

The eight-state named geography/authority candidate enumeration pass has been ingested and audited: AK 1, DC 1, HI 4, IL 108, MN 87, MO 116, NH 234, RI 39 (**590/590**). Nationwide named primary candidates: **3,769 / 6,217** against provisional denominators. Remaining unenumerated units in the tracker: **WI 1,850, MA 351, VT 247** (2,448 total).

Evidence and semantics:
- 2025 Census Gazetteer county-equivalent names back the county-shaped candidate rows for MN, IL, MO and HI. Hawaii Kalawao is not an independent county election division and is intentionally excluded.
- Rhode Island state GIS identifies its 39 municipalities; New Hampshire state planning office publishes a headerless official 234-municipality CSV, excluding additional unincorporated areas found in GIS.
- IL six municipal election commissions are explicitly listed by the Illinois State Board of Elections; Missouri's Kansas City Election Board is distinct from the Jackson County board.
- AK and DC are modeled as single state/district election authorities.
- **Caution**: IL's 102 county-equivalent candidates plus six city commissions meet the provisional 108 count but do not yet prove that every Census geography maps one-to-one to one of the state's 102 county-level election authorities (some may operate under commission arrangements). Similar caveat for MO: 115 county/city geographies plus the separate Kansas City election board, and Kansas City's board covers only the Jackson County portion of the city. Crosswalk authority identities and overlapping jurisdiction boundaries before considering these verified independent authorities.
- These additions are enumerated_unresolved: no local election-result endpoints were verified by this import. Statewide directory fallbacks do not constitute verified local result access, and population/reporting-place-weighted actual coverage is still not computed.
- scripts/ingest_priority_state_rosters.py is reproducible/idempotent; its GitHub workflow is manual-only after the successful initial import. Keep the registry and derived tracker synchronized whenever re-running.


## Single bounded revisit: WI, MA, VT (October 9, 2026)

- **Massachusetts: SUCCESS.** State-origin MassGIS ArcGIS municipal polygon feed returned 351 distinct named municipalities against the expected 351. All 351 were imported as `enumerated_unresolved`, source-provenance retained. This is geography enumeration, not election-result URL verification.
- **Vermont: DEFER.** State VCGI ArcGIS BNDHASH town layer returned **256** distinct geographic polygons/names, while our authority denominator is **247** cities/towns. Nine unorganized towns/gores explain why the broader geography count differs; must explicitly classify exclusion from the state legislature's official list instead of arbitrarily truncating or treating the polygon list as 247 incorporated election authorities. Source: https://services1.arcgis.com/BkFxaEFNwHqX3tAw/arcgis/rest/services/FS_VCGI_OPENDATA_Boundary_BNDHASH_poly_towns_SP_v1/FeatureServer/0/query ; crosscheck https://legislature.vermont.gov/assets/Clerk-of-the-House-Documents/District-Lists-and-All-Member-Info/250930-House-District-List-2025.pdf.
- **Wisconsin: DEFER.** A clean source-backed extract of municipal and county *election clerk* authorities has not been reconciled to the provisional 1,850 count. The Wisconsin Elections Commission clerk directory is the official start: https://elections.wi.gov/clerks/directory. The 1,850 may combine overlapping municipal and county tiers; do not fabricate 1,850 identities from county or place names.

After this bounded pass, nominal enumeration rose to **4,120 of 6,217**. The unresolved enumeration counts are **WI 1,850; VT 247**, 2,097 total. The count remains provisional and does not certify direct result-source coverage or independently verified election administration identities. Bounded one-pass import script: `scripts/ingest_three_state_rosters.py`; workflow is manual-only after the successful batch. The remaining two are deferred pending a genuine official-authority crosswalk, not an indefinite scraper loop.


## Vermont resolved — October 9, 2026

The Vermont state GIS contains exactly 256 town-equivalent geographic areas. Vermont's official state legislative roster separates 247 organized towns/cities from nine unorganized towns/gores: Averill, Avery's Gore, Buels Gore, Ferdinand, Glastenbury, Lewis, Somerset, Warner's Grant, and Warren's Gore. The state election wards mapping explicitly excludes those nine because they have no independent municipal government or local election-result reporting. Their residents vote for state/federal office through organized municipality checklists (17 V.S.A. § 2123). With those nine excluded *explicitly*, the state GIS reconciles to 247 of 247 incorporated municipalities. All 247 have been imported as enumerated_unresolved; none are newly certified direct result URLs. The nine non-reporting areas remain represented in documentation and require no fictitious standalone election authority.

References: https://legislature.vermont.gov/assets/Clerk-of-the-House-Documents/District-Lists-and-All-Member-Info/250930-House-District-List-2025.pdf ; https://www.arcgis.com/sharing/rest/content/items/fae5aad934a74108812dbe8ecd6232d4/info/metadata/metadata.xml?format=default&output=html ; https://legislature.vermont.gov/statutes/section/17/043/02123 .

After reconciliation, national provisional named-unit enumeration is **4,367/6,217**, with Wisconsin's **1,850** as the *only* remaining unnamed provisional denominator. This supersedes the prior Vermont-deferred note. The roster importer was returned to manual-only dispatch after successful GitHub Actions import and derived tracker regeneration.
