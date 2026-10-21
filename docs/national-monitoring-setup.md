# Schedule national discovery monitoring

## Automated directory expansion and discovery

Fresh web-search leads are also loaded automatically from
`registry/local_site_discovery_leads.csv`. The separate hourly search automation
uses unresolved jurisdictions to extend that ledger; see
[the discovery-loop contract](local-site-discovery-loop.md). These inspection
targets retain evidence and do not change verified source coverage.

`national-results-watch.yml` adds a GitHub Actions run hourly and a
manual dispatch. The schedule only becomes active after the workflow is on the
default branch; a PR or local dry run is not deployment. Scheduled Actions can
be delayed by GitHub and do not guarantee a one-hour service level.

Each run builds inspection seeds from uniquely labeled, hash-backed HTML website
leads in the checked-in directory report and the preceding worker's directory
queue. Ambiguous labels, artifacts and unsafe URLs remain outside HTML fetching.
These are unverified inspection associations, never promoted official sources.
The generated `directory-seeds.csv` retains directory URL, unit, match basis and
capture digest. Alternative unit associations are preserved for review.

The watcher follows observed results candidates to depth two, at most 40 pages
and 100 requests per pass, with a six-hour successful-page revisit interval and
an 8-minute cooperative network budget and a 12-minute watchdog. New/unvisited targets precede revisits. Discovery
is separate from election-night vote ingestion; this cadence does not promise
rapid result-total updates. Robots limits remain enforced per host.

Runs are serialized. The v2 cache retains control state and the authority queue;
per-run captures/journals/exports are compressed into a recovery artifact requesting
90-day retention. A separate v1 restore migrates old state once. See
[national-results-watch-operations.md](national-results-watch-operations.md) for
checkpoint recovery, queue semantics and time-budget behavior. Discovery does not
collect changing vote totals; use the [election-night runbook](election-night-runbook.md)
for the independent selected-feed collector.

Reproduce inventory preparation locally:

```sh
python -m scripts.build_directory_watch_seeds
python -m scripts.watch_national_results --directory-seeds watch-data/directory-seeds.csv --dry-run
```

## Persistent worker alternative

This worker watches official starting pages and already observed result-page
candidates. It detects page changes, recognizes result links with the fingerprint
catalog, and queues newly observed endpoints. It does not yet parse changing vote
totals, certify served jurisdictions, or verify election-night feeds. The GitHub discovery schedule is deployed on main; a separate persistent worker
is an operator alternative.

The checked-in inventories yield 1,134 eligible unique HTML targets. Additional
observed HTML candidates are followed on later passes, through depth two by default.
Linked binary/structured artifacts are retained as inspection leads rather than
sent through the HTML watcher. The first pass establishes a baseline: a candidate
new to the watcher is not necessarily a newly published website.

## Install and inspect the inventory

On a persistent macOS/Linux worker, clone the repository and check out
`main`. From the repository root:

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -e '.[dev]' 'httpx[socks]'
.venv/bin/python -m scripts.build_national_layer_frontier
.venv/bin/python -m scripts.watch_national_results --dry-run
```

The dry run makes no network requests or state writes. It lists eligible target
count and limits. Use `--states MI OH` to inspect or run a smaller starting slice;
that selection applies to both registry seeds and followed candidates. Generated
source seeds are included when available; missing source-seed files simply leave
the starting-page inventory in use.

## Run one bounded pass

```sh
.venv/bin/python -m scripts.watch_national_results \
  --state-dir watch-data \
  --interval 3600 \
  --max-pages 100 \
  --max-requests 300 \
  --max-depth 2 \
  --delay 1
```

`--interval` controls when each successful page becomes due again. Scheduling the
command more frequently drains unvisited/due targets; it does not refetch pages
that are not yet due. Earliest checked/unvisited targets receive priority across
states, preventing later states from being starved by a small batch. Failed
fetches back off exponentially up to one day. All requests, including robots and
redirects, share the request cap. Robots rules and crawl delays are respected;
robots redirects, HTML challenges and unavailable rules remain unresolved.

The worker runs sequentially with host pacing. It has no throughput benchmark
against the national live sites yet. A 100-page batch needs at least 12 passes for
the initial 1,134-page inventory, and redirects, timeouts and new targets can extend
that. Do not equate a one-hour page interval with a guaranteed one-hour full sweep.

## Schedule on a worker

Create a log directory in your checkout, then use a scheduler such as cron. This
example runs a bounded pass every 15 minutes. Replace `/absolute/path/ElectionDataGrabber`
with your checkout path; paths containing spaces require shell quoting.

```sh
mkdir -p watch-data
```

Add this entry with `crontab -e`:

```cron
*/15 * * * * cd /absolute/path/ElectionDataGrabber && .venv/bin/python -m scripts.watch_national_results --state-dir watch-data --interval 3600 --max-pages 100 --max-requests 300 >> watch-data/worker.log 2>&1
```

This is a setup example, not an installed schedule. macOS launchd can invoke the
same command. An advisory lock prevents overlapping processes from writing the
same state directory. Keep the worker awake and retain the same state directory
across restarts; changing it intentionally starts a new baseline.

## Outputs and readiness

- `watch-data/state.json`: atomic checkpoint, latest successful pages, retained
  candidates, due times, fingerprint version and last 1,000 events.
- `watch-data/snapshots/`: content-addressed captured UTF-8 HTML, including blocked
  captures for local investigation. These represent decoded HTML, not original wire bytes.
- `watch-data/events/`: durable per-page change journals with sequence IDs. A crash
  before checkpoint commit can leave an uncommitted journal; consume committed
  state/event IDs and deduplicate journal records by sequence and content.
- `watch-data/candidate-queue.csv`: candidates, parent pages, recognition rules,
  observation times and snapshot hashes, ready for the inspection/adapter stage.
- `watch-data/authority-link-queue.csv`: observed links from registered state
  directory/authority pages, with state-scoped unit-label matches and snapshot
  evidence. Ambiguous and unmatched links remain separate review work. See
  `docs/authority-directory-frontier.md` for replay and registry promotion.
- `watch-data/last-run.json`: checked pages, request count, new candidates,
  remaining due pages, unvisited pages and oldest due lateness.

If due-page backlog or lateness grows, the configured worker is not meeting the
desired revisit rate. Measure actual requests, latency, host limits and failures
before changing cadence/budgets or adding workers. Keep discovery polling distinct
from the faster polling of selected result feeds once reporting begins.

Removed links remain historical leads. Blocked/failed responses retain the last
successful snapshot and are never interpreted as source absence. Unknown query
tokens and contact labels are kept out of the candidate export. Raw snapshots and
worker logs remain local and should not be checked into the repository.

Validation: offline regressions cover restart/due scheduling, state fairness,
link removal/reappearance, blocked-page retention, request exhaustion, robots
checks on redirects, worker locking and bounded follow-up. Actual national network
reachability, scheduler deployment and election-night latency remain unverified.
