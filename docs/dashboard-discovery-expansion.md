# Discovery catalog expansion — October 9, 2026

This documents the earlier 749-URL snapshot. See [the continuation report](dashboard-discovery-continuation.md) for the current catalog and payload validation.

The first pilot produced raw candidate evidence. This continuation adds a filtered,
reviewable source-lead catalog and a second nationwide pass on draft PR #70.

## Findings

`registry/discovered_result_sources.csv` contains **749 distinct observed URLs**:

| Catalog kind | URLs |
|---|---:|
| Dashboard candidates | 140 |
| Results artifact leads | 222 |
| Results page/index leads | 365 |
| Authority CMS pages | 22 |

Applying the same source filters to the original pilot yields 303 catalogable URLs;
the expansion adds **446 URLs**. That baseline is deliberately different from the
pilot's 577 raw publisher leads: script assets and unrelated artifacts are removed.
The combined catalog has evidence attribution to **34 states plus DC**, and 685 of
its URLs are absent from the existing starting-point inventory. These are URL discoveries,
not new verified publishers, independently served jurisdictions, or coverage estimates.

234 cataloged targets have a successful HTML fetch; 490 have not been fetched and 25 have
fetch failures. Successful fetches include
application shells that need a browser or structured-data probe. No numeric-results
verification was completed, and **verified live sources remain zero**.

Platform evidence includes 49 Clarity records, 37 Enhanced Voting records, 79 public
results-app path records, and one Quest ENR record. These counts overlap. PDF and tabular
artifact families account for 213 and 9 records respectively. Historical election
labels are retained rather than being relabeled as current election-night sources.

## What changed

- Wired the existing 51-state/DC results-surface registry into the starting-point
  inventory as candidate leads. County-scoped Utah evidence stays county-scoped.
- Catalog version 3 adds observed government-host Enhanced Voting evidence (Georgia,
  Utah and Virginia), the public-results path shape, CivicPlus script evidence as CMS,
  and the Quest brand plus ENR asset signature observed on Indiana's state portal.
  Exact hostname boundaries are tested; generic public-results paths remain heuristic.
- Honors observed HTML `base` tags, fixing relative asset/target resolution in custom
  government-host dashboards. Canonical publisher grouping preserves election/tenant IDs.
- Saves optional immutable HTML snapshots and observation timestamps. Offline replay
  verifies snapshot digests, preserves CRLF bytes, and reevaluates current fingerprints
  without a network crawl.
- Distinguishes HTML access-rejection pages from successful content, application shells
  from HTML content, and non-HTML artifacts from failed HTML fetches. New Mexico returned
  a rejection page with HTTP 200 and is placed in the unresolved backlog.
- Exports a deterministic source catalog with original evidence pages, families, scores,
  observed year/label strings, source scope, fetch state and digest references. State
  attribution describes where a link was observed; it never asserts who a publisher serves.

The catalog's verification status is conservatively `candidate` or `fetched_unverified`,
plus explicit failure/artifact states. The batch's separate jurisdiction-specific
`context_supported` field is triage evidence only. All served-jurisdiction and live
coverage flags remain false. Registries governing established capabilities are untouched.

## Bounded collection and evidence

The expansion selected 200 additional registered non-artifact locations across 48 states,
excluding previously attempted URLs. The broad pass used **350 capped HTTP attempts**,
including redirects, and recorded 313 page attempts. Its initial live output had 174 HTML
fetches, 138 failures and one artifact. Offline replay then reclassified captured HTML
under catalog v3 and removed blocked content from candidate discovery.

A targeted pass fetched 50 already observed dashboard URLs, prioritizing literal 2026
URL/label evidence. It used 50 HTTP attempts and produced 27 HTML fetches and 23 failures.
Thus the two production batches used **400 additional HTTP attempts**, plus 10 separate
supporting probe targets. Supporting probes are outside the batch counters; redirects
can add requests. Referenced Indiana application scripts returned HTTP 400, so their
suggested data paths were not invented or treated as reusable feeds.

Included audit files:

- `expansion-seeds.csv` and `targeted-seeds.csv`: observed/registered entry points.
- `expansion-live-summary.json`: original catalog-v2 live collection.
- `expansion-summary.json`: final catalog-v3 offline replay.
- `targeted-summary.json` and `catalog-summary.json`: explicit costs and counts.
- `dashboard-evidence.jsonl`: observed dashboard target provenance.
- `unresolved-pages.csv`: failed, blocked and application-shell inspection backlog.

Raw HTML, full candidate output and resume checkpoints remain local and ignored. To
collect a new bounded batch and produce a catalog:

```sh
python -m scripts.discover_national_results --seeds audit/dashboard-discovery/expansion-seeds.csv \
  --max-publishers 200 --max-requests 350 --election 2026 \
  --snapshot-dir audit/dashboard-discovery/snapshots \
  --checkpoint audit/dashboard-discovery/new-expansion-checkpoint.json
python -m scripts.catalog_discovery_results \
  --batch audit/dashboard-discovery/new-expansion-checkpoint.json audit/dashboard-discovery/expansion-seeds.csv \
  --observed-date 2026-10-09
```

Replay uses `scripts.replay_discovery_snapshots` with `--captured`, `--seeds`,
`--snapshots` and a separate `--output` checkpoint. Existing catalog/config mismatches
still require a new checkpoint; raw captures can be deliberately replayed under a new
catalog. Concurrent jobs must use separate checkpoint paths.

## Validation and next pass

The full local suite passes (**385 tests**), including regressions for custom-host base resolution,
CMS/result separation, access-rejection HTML, artifact states, Quest signature
specificity, large negative HTML pages, snapshot integrity and source-catalog filtering.
The national starting-point audit still counts all 6,288 units; this does not establish
100% source coverage. Hosted CI results are reported on draft PR #70.

Next, review the 140 dashboard candidates by publisher/election identity, obtain actual
structured result payloads, and verify authoritative served jurisdictions. Use the
unresolved backlog for browser escalation and artifact inspection. Expand locality
entry points outside the existing MI/OH/ME-heavy local registries before measuring
nationwide local discovery precision. Do not promote coverage from platform matches,
year tokens, application shells, or common government hosts.

Publication excludes bot-protection/session URLs and redacts email addresses from link
labels. The public catalog also excludes URLs with unclassified refresh/hash/revision query
parameters. All 140 dashboard candidates remain in the public catalog; other excluded
leads remain in local captures for query-purpose review. These metadata exclusions do not remove
functional election, county, tenant or year query parameters.
