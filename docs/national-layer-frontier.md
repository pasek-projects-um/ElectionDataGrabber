# National discovery layers — October 10, 2026

The acquisition priority is to clear the national layers in order: expected units,
named units, official starting pages, linked result sites, then reporting-unit and
payload detail. A successful historical parser is useful, but does not substitute
for identifying the local authorities and their websites nationwide.

## Current evidence

| Layer | Recorded position | Remaining work |
| --- | --- | --- |
| Primary unit enumeration | 6,288 expected and named units across 50 states plus DC | 46 state denominators remain provisional; equality of counts does not validate the authority model |
| Local starting pages | 191 named units have direct registered leads | 6,097 have state fallback pages only; resolve local authorities from those directories |
| Exact local page-to-source paths | 20 units have observed child leads from their exact registered direct pages | 171 other units with direct starts need link extraction or provenance reconstruction |
| Observed source catalog | 940 distinct URL tasks, attributed to 34 states plus DC | Inspect links and artifacts; state attribution is not a verified service area |
| Shared starting pages | 627 unique starting URL tasks | Crawl each shared state directory once and retain all unit associations |

These are offline joins of checked-in evidence, not a fresh crawl. The 20 exact
local paths are a conservative subset: paths through redirects or intermediate
pages that lack an exact recorded join remain unresolved. A state directory's
children are not assigned to every local unit merely because those units use the
directory as their fallback. Same-host URLs are not treated as locality matches.

## Reproducible national queues

Run from the repository root:

```sh
python -m scripts.build_national_layer_frontier
```

`audit/national-layers/` contains:

- `layers-by-state.csv`: all 51 jurisdiction summaries, including denominator review.
- `unit-next-actions.csv`: all 6,288 named units with direct/fallback URLs and the next action.
- `unique-start-pages.csv`: 627 deduplicated starting pages, directory layer first.
- `source-next-actions.csv`: 940 observed sources with parent-page provenance and routing.
- `summary.json`: aggregate counts, scope, and explicit zero network requests.
- `watch-fingerprints.csv`: the existing evidence-backed recognition rules, exported
  with their matching field, pattern and provenance for the watcher.

The source queue routes 343 artifacts to inspection, 139 dashboards to payload/link
inspection, 408 result pages to link extraction, 25 CMS pages to authority-link
extraction, and 25 failed targets to investigation. Failures do not establish that
a source is missing. None of these new queue associations verifies jurisdiction
service or election-night refresh behavior.

## Next collection pass

1. Review provisional authority models against official directories, keeping
   counties, municipalities, independent cities, and election authorities distinct.
2. Work directory tasks in state rounds across the nation. Extract observed
   authority/homepage links with labels, parent URLs and snapshots. Do not guess URLs.
3. Match directory entries to named units with explicit evidence; retain ambiguous
   entries for review and report unmapped named units separately.
4. Follow each local starting page into election office, selector, archive, result
   portal and artifact links. Preserve every edge and deduplicate shared targets.
5. Group the resulting drill-down work by platform family, then inspect reporting
   units and payloads. Record historical, executable and refresh-verified maturity
   separately.

This pass should broaden local starting-page evidence outside the existing
Michigan/Ohio/Maine concentration before interpreting national coverage rates.

## Pre-election hunting signals

The live page may not be published until near election day. A starting page is a
place to watch even when it has no current feed. Every start task carries watch
signals and `unpublished_feed_status=unresolved_not_missing`; it is not classified
as a missing source. This work generates the watch queue, not a running scheduler.

The existing fingerprint catalog distinguishes strong host/path signals from weak
branding and CMS evidence:

| Signal already implemented | What to look for | Interpretation |
| --- | --- | --- |
| Clarity | Observed hosts ending in `clarityelections.com` | Result-platform candidate; retain jurisdiction/election path pieces |
| Enhanced Voting | `app.enhancedvoting.com/results/public/` and observed government hosts | Follow actual public election selectors and their election-specific links |
| Public-results applications | `/results/public/{publisher}/elections/{election}` or supported related paths | Candidate path family; no invented publisher/election IDs |
| Quest ENR | Quest branding together with `Scripts/EnrAngular/` assets | Application evidence, not parsed or live results |
| Scytl / Electionware | Observed branding and linked report evidence | Follow up for actual endpoints or supported artifacts |
| CivicPlus / CivicEngage | CMS branding/assets | Useful authority-site lead; no result-platform claim |
| Structured/document artifacts | Linked CSV, Excel, XML, JSON, ZIP and PDF under result context | Payload lead; extension alone does not establish election relevance |

At each refresh, preserve the page snapshot and compare newly observed links,
election selectors, iframe targets, script/embedded endpoints, and redirects.
Retain older leads when a page temporarily removes a link. Blocked pages and app
shells need follow-up, not absence claims. Confirm jurisdiction, election context,
actual payloads and repeated updates before promoting a candidate to a live feed.
Historical URL pieces guide recognition of observed links; they do not authorize
guessing new URLs or imply that a future election uses the same endpoint.

Keep three hunting paths explicit: already observed result-page candidates;
historical endpoint reconstruction from official archives, prior election links
and Internet Archive captures; and future publication watches on known parent
pages. These paths may coexist for one locality. The source queue retains observed
years and election labels as clues, while every start task names the historical
recovery sources. Historical URL reuse requires fresh observation and context;
neither an old capture nor a currently accessible page verifies live updating.

Most feeds cannot be verified for actual results and updates until post-election
reporting begins. Before then, measure hunting readiness: identified authority,
known parent pages, historical endpoint evidence, recognition signals, and unresolved
paths. Keep that readiness separate from post-election payload and refresh
verification; a lack of published results before the election is expected.

The repeatable watcher is now implemented in `scripts/watch_national_results.py`.
See `docs/national-monitoring-setup.md` for bounded runs, persistent state, scheduler
setup, detection outputs and the remaining deployment/live-ingestion boundary.
