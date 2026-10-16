# Fresh local-site discovery loop

Two independent schedules cooperate: the GitHub discovery watcher runs every
half hour; the ChatGPT Election discovery loop runs hourly and performs fresh web
searches. The watcher alone does not search the web. Search scheduling is managed
outside GitHub; check that automation separately from Actions.

Each search round reads `audit/authority-directory-national/unit-readiness.csv`,
`registry/us_primary_election_localities.csv`,
`registry/local_site_discovery_leads.csv` and
`audit/local-site-discovery-attempts.csv` from the latest main branch.

1. Select up to 20 unresolved jurisdictions without an existing fresh lead.
   Rotate across states, prioritizing states least recently attempted, then
   never-attempted units and tractable county election authorities. Within a
   state prefer an unattempted unit over an already searched one. Do not retry
   unsuccessful searches within 24 hours. Keep municipal gaps in scope and do
   not change the national denominator.
2. Batch web searches using exact unit name, full state name, and election office
   or results terms. Open promising official pages to inspect the actual evidence.
   Follow official references to additional directories where useful. At most
   two queries per unit and ten minutes of work per round. If a search tool is
   unavailable, report that blocker rather than claiming fresh discovery.
3. Record actual observed URLs only. Use exact canonical jurisdiction IDs and
   state, an evidence-page URL in `discovered_from`, a concise factual excerpt or
   paraphrase in `evidence_excerpt`, a timezone-aware ISO `observed_at`, and
   `evidence_status=observed_link_candidate`. A page can be its own evidence
   source when its content identifies the jurisdiction and election purpose.
   Do not generate domains, infer missing links, assign same-named places across
   states/counties, bypass access restrictions, or label candidates verified/live.
   Historical pages are valid leads; describe historical context explicitly.
4. Append a row per completed unit attempt, including query, time and outcome,
   even when no usable lead was found. Preserve existing rows, alternative URLs
   and provenance; deduplicate leads by unit, normalized URL and evidence source.
5. Validate candidate rows using `inspection_seeds` in
   `src/election_data_grabber/local_site_discovery.py`, ideally run
   `python -m scripts.watch_national_results --dry-run`, and publish only the two
   CSV data files to main with GitHub tools. Prefer a single atomic Git-tree
   commit with an expected-head lease. On a head conflict, reread main and merge
   data rows before retrying. Never overwrite concurrent changes. Changes to
   code/workflows require a tested PR rather than a direct data commit.

The next watcher checkout automatically reads the fresh-lead ledger, validates
IDs/state/provenance and follows observed result links from these new starts.
Updates to the lead ledger on main also trigger the watcher immediately; the
half-hour schedule remains a fallback. Runs share the same concurrency group.
Invalid ledger rows fail visibly rather than silently disappearing. The first
four leads (Autauga AL, Apache AZ, Adams CO, Alachua FL) were inspected October 16
UTC. They are candidates, not newly verified election-night feeds.

The search task also checks recent Actions runs, checkpoint restoration, backlog
and distinct-URL growth. Report meaningful new results and actionable failures;
avoid routine no-change notifications. Cache loss starts a new watcher baseline;
recovery artifacts and the committed lead/attempt ledgers remain separate.
