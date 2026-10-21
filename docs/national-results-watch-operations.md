# National discovery watch execution

The failures in runs 39600378538 and 39599304192 both reached GNU timeout's
20-minute limit (exit 124) during a crawl-delay sleep in Fetcher. They restored
~345 MB caches and uploaded 69,240 / 69,200 files, respectively. Artifact sizes
were 517,223,131 / 516,851,627 bytes. Completed pages had atomic checkpoints,
but interruption skipped candidate exports and final progress summaries.

The watch now runs hourly, serializing all schedule, push and manual invocations
with one concurrency group and cancel-in-progress false. GitHub retains a running
job and at most one pending job in this group; pending invocations can coalesce.
Do not use this schedule as an ordered task queue. Forty selected pages, 100 HTTP
requests (including robots and redirects), and 480 seconds of cooperative network
work replace the 200-page / 600-request pass. The 12-minute shell watchdog is an
unexpected-stall failure guard, not a normal successful exit. The job ceiling is
20 minutes, leaving packaging and upload time. Time/request/page exhaustion is a
successful partial batch; unrelated exceptions still fail the job.

Deadlines are checked before pages, host waits, redirects and response chunks.
SIGINT/SIGTERM request a cooperative stop. Existing HTTP operations retain their
15-second inactivity timeout; parsing, checkpoint serialization and exports are
not preempted. Host waits are interruptible in 250 ms slices. If the remaining
budget cannot accommodate the crawl delay plus 20 seconds of request headroom,
the host is deferred until its delay expires without recording a fetch failure.
Other selected hosts can proceed. Robots rules and wall-clock host request times
are checkpointed across processes. Rules are refreshed after 24 hours or twice
the host delay, whichever is longer, so a long delay does not repeatedly fetch
robots and indefinitely defer the results page after every restart. Deferred work and unstarted pages remain in the
checkpoint's due queue. Oldest/unvisited pages with state round-robin selection
continue on subsequent invocations; no cursor depends on an unstable URL offset.

Only state.json and authority-link-queue.csv are cached under v2. Candidates,
associations, page statuses, due times and event sequence are retained in state.
CSV exports are regenerated. On a v2 cache miss a separate v1 restore attempts a
one-time migration of the full legacy directory, preserving the old checkpoint.
That first run can still have a large archive. Subsequent fresh runners capture
only that run's snapshots and event journal, rather than restoring historical
snapshot/journal files. The archive also includes the complete control checkpoint
and CSV exports, so artifact recovery is possible after cache eviction.

watch-evidence.tar.gz preserves files without deleting snapshots or journal
entries; manifest.json reports file count and compressed/uncompressed bytes.
Upload uses compression-level 0 because the archive is already compressed.
Artifacts request 90-day retention (subject to repository/organization policy).
Caches are an evictable acceleration layer, not permanent evidence storage.
Keep the first migration archive and subsequent run artifacts if long-term audit
retention is required. Earlier ~517 MB artifacts are untouched. Historical hash
references may require an earlier artifact or the migration archive; the current
artifact does not claim to contain all historical evidence. A cache miss with no
legacy cache starts fresh; restore an artifact checkpoint manually to recover it.

Each completed page logs checked-page/request/elapsed counters. last-run.json and
the Actions summary include stop reason, elapsed seconds, page-status counts,
remaining due/unvisited pages, lateness, candidate/event totals, request count and
checkpoint bytes. host_deferred counts scheduling decisions, not successful HTTP
fetches. Packaging reports artifact sizes independently. A first live post-merge
run is still needed to measure production sizes and throughput; smaller budgets
can increase backlog latency. Follow-up depth remains at two.

All discoveries remain candidates. Signatures, link labels and geography clues
never establish service jurisdiction or verified election-results coverage.
Candidate exports retain served_jurisdiction_verified=false and live_coverage=false;
summary live_sources_verified_this_run remains zero. Snapshot hashes, associations,
event sequence and existing verification boundaries are preserved.

Regression CI exercises deadline restart, request exhaustion, crawl-delay host
scope/deferral, fairness, evidence packaging, robots enforcement, candidate safety,
and existing discovery policy and directory-seed tests without live crawling.
