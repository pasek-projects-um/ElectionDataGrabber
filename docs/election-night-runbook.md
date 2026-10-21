# November 2026 election-night collector

This is the operator path for explicitly selected feeds. National discovery runs
separately and never enables a candidate URL automatically. The collector supports
CSV, the generic reporting-unit JSON contract, Clarity-like XML, Enhanced Voting
embedded JSON and Washtenaw production HTML. A vendor name or filename extension
does not establish schema compatibility. XLS/PDF/ZIP and multi-page crawling are
outside this first collector path.

## Current release evidence

On October 21, the discovery repair completed production runs 39638214492 and
39642718109. The latter checked 40 pages / 54 HTTP requests in 223.1 seconds and
uploaded 6,068,288 bytes, versus about 517 MB in the earlier failures. It still had
8,304 due pages and a 146,773,358-byte control checkpoint. Discovery throughput and
its large candidate graph remain separate work; they cannot provide minute-scale
vote collection.

The real Washtenaw August primary rehearsal exposed and fixed two production
adapter defects: two-cell `.headertr` contest headings (including district numbers)
and a hardcoded August election ID. The collector acquired and replayed 3,464
county-summary observations from the official August 2026 page, with SHA-256
750d0b340ada891f3ec35daa453ea9c29f8deab251f2151acc7565892e8199b1.
The source timestamp was August 31, 2026, 11:33:05 a.m. America/Detroit. This is
historical rehearsal evidence, not proof of November refresh, precinct completeness,
or the coverage of every contest/geography represented by a county's aggregate.

`config/election-night-2026.json` intentionally has no enabled feeds. No November
payload was adjudicated by this implementation. An empty manifest fails the
collector/status health gate; a passing code rehearsal is not operational release.
The checked-in readiness snapshot records its input file hashes. Regenerate it
when registries change; CI publishes a current report artifact.

## Install, inspect and rehearse

From a checkout of main:

```sh
python3 -m venv .venv
.venv/bin/pip install -e '.[dev]'
.venv/bin/election-grab readiness
.venv/bin/pytest -q tests/test_election_night.py
```

An optional live historical smoke test uses one official county-summary page:

```sh
.venv/bin/election-grab collect config/washtenaw-2026-primary-rehearsal.json \
  --state-dir rehearsal-data --time-budget 45
.venv/bin/election-grab status config/washtenaw-2026-primary-rehearsal.json \
  --state-dir rehearsal-data
```

The manifest labels it as the August primary, not the general election. It does
not fetch the county's linked precinct pages. Source timestamps remain distinct
from acquisition timestamps. The adapter's legacy default election ID remains for
backward compatibility; this collector always supplies the configured election ID.

For an offline replay, use the sample path printed by collect, for example:

```sh
.venv/bin/election-grab replay rehearsal-data samples/ACTUAL_SAMPLE_HASH.json
```

The ACTUAL_SAMPLE_HASH placeholder must be replaced by a path from your run.
Replay reads preserved bytes and the original feed configuration/acquisition time,
checks raw and normalized-file hashes, and requires an exact normalization match.
It performs no network requests. CI simulates updates, unchanged/304 responses,
corrections, row removal, outages, parser failures, config changes, restart and
artifact corruption across the supported parser families.

## Select a November feed

Add a feed to `config/election-night-2026.json` only after independently checking:

1. The exact observed artifact URL belongs to the intended authority and election.
   Record both `authority_evidence_url` and `election_evidence_url`, and the actual
   timezone-aware `reviewed_at`. Do not invent a November URL from an August path.
2. The payload matches one of the named parser contracts. Set a `required_text`
   marker when the payload provides an election label. The collector cannot infer
   election identity from arbitrary bytes; an operator-selected URL is still an
   assertion that requires this adjudication.
3. Use a stable `source_id`, canonical state/jurisdiction and independent authority
   ID. Each source is a separate outlet; county/state/vendor mirrors are never
   summed together. Multiple feeds may serve one jurisdiction without changing its
   denominator. Source ordering in a manifest never becomes identity.
4. Specify `update_semantics`: cumulative, incremental or unknown. Polling never
   blindly adds successive snapshots. For cumulative feeds, decreases require
   review. For a Washtenaw summary, configure an explicit `reporting_unit_name`
   and `reporting_unit_type=county`; do not label summary totals as precinct data.
   Specify `source_timezone` when the source's timestamp lacks an offset.
5. Choose `interval_seconds` (at least 30) and `stale_after_seconds` (at least the
   interval). Robots rules, host delays and shared request/byte budgets still win.
   Test a baseline and another due poll; replay the captured sample independently.
6. Enable only the reviewed feeds. Obtain real changing November captures before
   asserting refresh verification. The collector reports `update_observed` as
   diagnostic evidence and never auto-certifies `refresh_verified` coverage.

The models reject unknown fields, duplicate source IDs, state/authority mismatches,
mixed election IDs, unsupported parsers and enabled feeds without dated evidence.
Changes to URL/parser/identity/review configuration invalidate the baseline and
conditional validators, preventing cross-election/config comparisons.

## Review actual refresh evidence

Automatic polling never certifies a feed. After observing a real current-election
update and checking its official provenance, an operator can record that review:

```sh
.venv/bin/election-grab verify-refresh config/election-night-2026.json \
  samples/OLDER_ACTUAL_HASH.json samples/NEWER_ACTUAL_HASH.json \
  --state-dir election-night-data --evidence-url https://OFFICIAL_OBSERVED_EVIDENCE_URL \
  --note 'Describe the official election identity and observed update you reviewed'
```

Replace the sample/evidence placeholders with actual run artifacts and observed
URLs. Both samples must be accepted collector attempts for the same current feed
configuration, independently replay successfully, have increasing acquisition times,
changed votes with continuous identities and no unresolved findings, and fall within
one day before through seven days after the configured election date (UTC acquisition
dates). This window admits election-night time zones and early canvass updates; it
is not a statement of any state's publication rules or certification deadline.
Historical rehearsals, unchanged payloads, changed configurations and unresolved
cumulative decreases cannot satisfy the gate. Review evidence remains source/election
specific and invalidates when configuration changes or artifacts become unreadable.
This review does not establish geographic completeness, independent mirror evidence,
or observed precinct visibility. Status still reports freshness failures separately.

## Persistent worker operation

Use a persistent macOS/Linux worker with local storage. One invocation is bounded
by `--time-budget` (default 120 seconds), `--max-feeds` (25), 200 shared requests and
10 MB per response. Robots responses and redirects count against request budgets.
An in-flight HTTP operation has a 15-second inactivity timeout; parsing and disk
I/O are not preempted. SIGINT/SIGTERM request a cooperative stop. Unstarted work
stays due; long-delay hosts are deferred; failed feeds back off to one hour.

Example minute scheduler on a worker, after the November manifest is populated:

```cron
* * * * * cd /absolute/path/ElectionDataGrabber && .venv/bin/election-grab collect config/election-night-2026.json --state-dir election-night-data --time-budget 45 --max-feeds 25 >> election-night-data/worker.log 2>&1
```

Create the state directory before enabling this cron entry. Replace the checkout
path and quote it if it contains spaces. No cron job is installed by this change.
A nonblocking process lock prevents overlapping collectors from writing the same
SQLite store. Separate state directories must not be used to evade host pacing.
GitHub scheduled Actions are not a minute-resolution collection service; this
workflow adds deterministic rehearsal CI, not a live election-night deployment.

Exit status 1 means no enabled feeds, stale accepted data, a fetch/parser failure
or an integrity review. `status` also fails for deferred/unpolled/unhealthy feeds.
Have the worker supervisor monitor these exits and disk availability. The tool
does not send notifications. A host deferral with an existing fresh baseline may
leave collect successful, but status exposes the deferral. Poll intervals are due
scheduling goals, not a guarantee of end-to-end latency.

## State, corrections and recovery

- `collector.sqlite3`: transactional per-feed due times, accepted baseline,
  validators, failure/backoff state, robots policy and attempt journal.
- `raw/`: immutable content-addressed acquired bytes, persisted before parsing,
  including payloads that fail normalization. CSV/JSON vote validation rejects malformed
  partial parses and missing/fractional/bool vote counts instead of silently imputing zero. Failed attempts retain raw references.
- `samples/`: immutable configuration, acquisition/response metadata, normalized
  observations, per-row snapshot hashes and change/review findings.
- `captures/`: lightweight response records referring to their normalized sample.
  Unchanged bodies/304 responses reuse raw and normalized samples.
- `last-run.json`: atomically replaced operator summary. SQLite is authoritative.

Each successful sample is reparsed from persisted bytes before the transaction
advances its baseline. Row identities include contest, choice, party, canonical
unit and raw/canonical vote mode. Ambiguous duplicate identities and negative
absolute votes fail normalization. Removed identities, identity discontinuity and
cumulative decreases are captured for review and do not replace the accepted
baseline. Failures in one feed leave other feeds and prior accepted results intact.

Freshness measures the last accepted transport/parse, not the recency of the
source's election totals. The report exposes source timestamps and last payload
change independently. No source timestamp means data freshness is unknown.
Legitimate corrections can decrease votes; inspect the retained sample, compare
with official evidence and update the reviewed configuration only after adjudicating
the correction. This intentionally starts a fresh baseline rather than silently
accepting a suspect transition. No automatic recovery from a corrupted baseline
is attempted; repair/restore preserved artifacts after investigation.

Back up the entire state directory together while the collector is stopped (or
use SQLite's backup API and a consistent copy of immutable artifacts). Restore DB,
raw and samples together. Copying only SQLite breaks replay; an orphan immutable
file after a crash is safe to retain. Disk failures are fatal infrastructure errors,
not source absence. No automatic pruning is implemented: provision/monitor disk and
retain archives according to the project's evidence policy. Locking assumes local
macOS/Linux filesystem semantics, not multi-host/network-filesystem coordination.

## Remaining November release gates

1. Populate and adjudicate the actual election-specific feeds for priority states
   and congressional/Senate jurisdictions; demonstrate parser compatibility per
   source. The November manifest currently contains zero feeds.
2. Deploy a persistent worker, durable storage/backups and supervisor health
   monitoring; measure latency/request budgets with the actual selected feed set.
3. Observe changing November payloads with stable unit/race identity; adjudicate
   cumulative corrections, timestamps, reporting topology and mirror overlap.
4. Reconcile source reporting places and geography against authoritative denominators.
   The current 6,288 named units and candidate URLs are not normalized coverage;
   46 state denominators remain provisional. Population/reporting-place weighted
   coverage is unknown until adjudicated deduplicated input mappings exist.
