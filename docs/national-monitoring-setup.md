# Schedule national discovery monitoring

This worker watches official starting pages and already observed result-page
candidates. It detects page changes, recognizes result links with the fingerprint
catalog, and queues newly observed endpoints. It does not yet parse changing vote
totals, certify served jurisdictions, or verify election-night feeds. It has not
been deployed or scheduled by this PR.

The checked-in inventories yield 1,134 eligible unique HTML targets. Additional
observed HTML candidates are followed on later passes, through depth two by default.
Linked binary/structured artifacts are retained as inspection leads rather than
sent through the HTML watcher. The first pass establishes a baseline: a candidate
new to the watcher is not necessarily a newly published website.

## Install and inspect the inventory

On a persistent macOS/Linux worker, clone the repository and check out
`codex/national-dashboard-discovery`. From the repository root:

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
