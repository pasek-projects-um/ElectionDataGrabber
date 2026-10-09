# Nationwide dashboard discovery, first implementation

Based on main `4d36952` (merged #68); implements the first phase of issue #69.

## Evidence and platform catalog

`registry/dashboard_fingerprints.json` is versioned data, independent of scraper code.
Each rule records an ID, family, field, pattern, role, specificity weight and repository
evidence reference. Clarity host boundaries and Enhanced Voting public paths carry
strong weights; the bare Enhanced host is weaker. Scytl branding is only a low-strength
lead, supported by the existing classifier, not a validated universal URL schema.
CivicPlus is authority discovery (zero platform weight); Electionware, PDF and tabular
files are report families. No new endpoint templates are guessed.

Score = maximum matching specificity weight + 20 for an election-results keyword,
capped at 100. Repeating the same signature cannot inflate a score. The scored record
includes all signatures, roles and provenance (page, target type, original URL, label,
keyword match). Generic sports results do not qualify. Artifacts without election
context remain low-score leads. Scores rank investigation; they are not probabilities.

Every observed anchor is inspected, along with iframe and script sources, canonical
links, meta refreshes, simple JS location assignments/replacements, fetch literals and
absolute quoted URLs. Scripts are never executed. HTTP redirects are followed manually
and bounded. Only HTTP(S) targets qualify; obvious private IP literals and localhost,
credentials and unusual ports are rejected. This is an operator-run research crawler,
not a hardened service for arbitrary untrusted seed submissions (DNS-based private
address rejection and robots policy remain future work).

Normalization preserves case-sensitive paths, tenant/election query parameters and
encoded slashes, removes fragments and tracking parameters, resolves relative URLs,
and decodes unreserved percent escapes. SPA hash views collapse to the underlying
resource. Clarity views collapse to state/county/election roots; Enhanced election
views retain tenant/election identity. Other publishers deduplicate only exact normalized
URLs: neither a common vendor host nor an authority link proves shared service.

## Batch and verification

Run from the repository after `pip install -e '.[dev]'`:

```sh
python -m scripts.discover_national_results --max-publishers 150 --max-requests 300 \
  --max-depth 1 --delay 1 --election '2026' \
  --checkpoint audit/dashboard-discovery/checkpoint.json
```

Default seeds use #68's where-to-look inventory and authority crosswalk. Selection is
state round-robin, preferring registered direct evidence over state fallbacks. Optional
`--seeds` CSV accepts `url`, `jurisdiction_id`, optional `authority_id`,
`jurisdiction_name`, `state`, and `page_role`. The legacy sweep remains unchanged for
its existing census consumers; this command is its evidence-scored successor.

CLI bounds: at most 200 seed locations, 1,000 HTTP requests (redirects included), depth
3, one request per host per second, six redirect attempts per target, 15-second HTTP
timeout, 1 MB response bodies and 50 ranked candidates expanded per page. Calls are
sequential. Script-only assets and non-HTML download URLs are not followed as dashboards.

Atomic checkpoints preserve fetched text, response digest, candidates, publishers and
separate authority/jurisdiction associations. Identical pages shared by multiple
jurisdictions are fetched once. Resume replays cached evidence without refetching;
failed pages require `--retry-failed`. Input, catalog and election/depth mismatches are
rejected. Use separate checkpoints for concurrent jobs. Request limits are per invocation;
seed selection can expand on resume, but changing seeds requires a new checkpoint.

States are deliberately distinct:

- `candidate`: observed target, not fetched.
- `fetch_failed`: HTTP failure, invalid redirect, byte limit, or artifact requiring inspection.
- `fetched_unverified`: HTML fetched, independent election/jurisdiction context incomplete.
- `context_supported`: target text contains results terminology, an explicit election
  token and a non-abbreviated jurisdiction name. This is triage evidence, not verification.

Association status is jurisdiction-specific; candidate records remain candidate evidence.
All `served_jurisdiction_verified` and `live_coverage` fields remain false. State fallbacks
and statewide aggregators retain their source scope and never become direct local coverage.
Manual review or a future structured adapter must establish authoritative publisher,
election, actual numeric results and reporting behavior before coverage promotion.

## Validation and pilot (2026-10-09)

`tests/fixtures/dashboard_discovery/observed-manifest.json` documents small observed
outbound-link excerpts from Ingham, Kent and Berrien official county pages, including
redirects. Their URLs were already registered; fixtures contain observed URLs rather
than synthesized live endpoints. The catalog was fixed before collecting these excerpts.
The old sweep's href URL keyword filter finds **0**, while the new catalog finds **18**
distinct Enhanced Voting links (8/2/8). This demonstrates discovery recall on a small,
vendor-focused held-out sample; it does not estimate nationwide precision or live coverage.

Synthetic fixtures separately exercise unlabeled links, archived results, CMS false
positives, sports links, PDF indexes, embedded dashboards, canonical/JS/meta/HTTP redirects,
normalization, separate tenants/elections, request bounds, failure retry, deduplication,
resume and independent context evidence. Three controlled negative cases produce no
results-platform matches. Brand tests cover Scytl and Electionware without pretending
those families have verified new production endpoints.

The live pilot selected **150 distinct registered seed locations across 50 states and DC**,
retaining 6,024 inventory associations (many are state fallback references, not publishers).
It consumed **220 HTTP requests**, recording **191 page attempts: 70 HTML fetches and
121 failures/artifacts requiring inspection**. This is a conservative crawl, so blocked
sites and downloads are not silently credited. `pilot-live-summary.json` preserves the
initial run; `pilot-summary.json` reports an offline replay through the final 50-candidate
expansion cap and stricter context checks. That replay identifies **577 candidate publisher
keys**, including 352 PDF signatures, 24 Enhanced public-path signatures and 3 Clarity
host signatures. Counts overlap and include historical/artifact leads. **Verified live
sources: 0.** The candidate evidence export and 150-row representative seed manifest are included
(the original 6,024 inventory associations are reproducible from the default inventory); the large
local resume checkpoint and raw text are ignored.

Full local suite: 371 passed. Two stale assertions failed identically on unchanged main:
source display order was asserted as ballot order, and a state/source-unspecified
`av_counting_boards` column was asserted as governed absentee. Tests now check the existing
conservative contracts, including unknown ballot order; production adapters are unchanged.
The new fixture CI runs the full suite without a network crawl.

## Next iteration

Manually adjudicate the strongest candidate publishers, record authoritative served
jurisdictions and election context, and connect structured adapter probes to verification.
Add independently reviewed Scytl/custom-host and CMS asset fingerprints; extend held-out
fixtures beyond Enhanced Voting. Separate non-HTML artifact inspection from fetch failures,
add robots/Retry-After policy and browser escalation for unresolved JavaScript shells,
and review false positives before expanding nationwide crawling. No registry coverage
flags are changed by this phase.

Continuation: [expanded source catalog and second discovery pass](dashboard-discovery-expansion.md)
documents catalog v3, additional state-surface entry points, snapshot replay and 446
additional cataloged URLs. The counts above describe the original catalog-v1 pilot.
