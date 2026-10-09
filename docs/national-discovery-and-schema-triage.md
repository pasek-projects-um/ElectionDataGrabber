# Nationwide election-site graph and model-assisted schema triage

## Durable source graph

Store one record per URL, not one URL per jurisdiction. Maintain typed edges:
`official_homepage -> elections_office -> voter_information -> election_selector -> election_results -> downloadable_artifact`.
Also support `historical_results`, `vendor_dashboard`, `state_directory`, and `municipal_homepage`.
A single URL may belong to several jurisdictions and elections. Keep explicit evidence for every association.

Minimum page metadata: URL, canonical URL, source jurisdiction ID, referring URL, page category,
discovered_at, last_checked_at, last_success_at, HTTP status, content hash, platform family,
election ID and cycle, confidence, evidence snippet, next_check_at, and failure reason.
Preserve known URLs across seasonal outages; distinguish historical evidence from live reachability.

## Discovery frontier

Seed from all known official authorities, election office directories, county/municipal homepages,
voter portals, archives, election selectors, and vendor endpoints. Prioritize by:
1. Newly changed pages and explicit current-year/general-election result links.
2. Previously verified live feeds and election-specific selector pages.
3. Known election offices, election sections, and archives.
4. Jurisdiction homepages and other indirect leads.

Bound crawl depth, requests per host, redirects, page size, and concurrency. Respect robots and
reasonable polling intervals. Use deterministic link classification first, model classification
for ambiguous cases, and record the reason for every promoted candidate.
Election-night fast polling is reserved for verified feeds, not arbitrary web pages.
Historical and pre-election crawling should never be confused with active results.

## Local Qwen roles

**Page triage:** Input a bounded plain-text extraction, link labels, URL and jurisdiction context.
Return structured JSON with page_type, election_cycle, platform_family, candidate URLs copied
from supplied links, next_action, confidence, and evidence. A model must not invent URLs.

**Schema triage:** When a new CSV, XLSX, PDF table, JSON or XML shape appears, pass a
privacy-minimized schema sketch: header names, representative sampled rows, types, surrounding
labels, provenance, jurisdiction, election, and known adapter expectations.
Return a *proposal* with per-field mappings to candidate, contest, party, votes,
reporting_unit, vote_mode, ballot_count, registered_voters, timestamp, or unknown;
include units, null semantics, evidence, confidence, and any aggregation risk.

**Never auto-promote model guesses into certified data.** Validate against known election IDs,
contest identities, jurisdiction/reporting-unit hierarchies, vote-mode exclusivity,
totals, duplicate rows, temporal consistency, and provenance. Unknown columns stay
raw and reviewable. Preserve original artifacts and model prompt/output versions for replay.
Use deterministic parser mappings after a schema is verified; do not run the model on every
poll of a stable dashboard.

## Mac Pro operational boundary

GitHub retains code, CI, test fixtures, and approved adapter mappings. A persistent local
worker on the Mac Pro owns the frontier, snapshots, classification queue, normalized store,
and restart checkpoints. The first milestone is a dry-run classifier that emits suggestions
without changing ingestion; next, audited schema mappings and a human-review queue; only
then allow validated mappings to be reused automatically. Benchmark Qwen size and
quantization on actual installed CPU/GPU, RAM and throughput.
