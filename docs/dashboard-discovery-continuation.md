# Discovery continuation and payload evidence — October 9, 2026

The current reviewed catalog contains **940 observed URLs**, up from 749: 193 new
leads and removal of a vendor login page and a sitemap. It contains 139 dashboard
candidates, 366 result artifact leads, 410 result page/index leads and 25 CMS pages.
Evidence attribution remains 34 states plus DC; this describes origins, not service
areas. None of these counts establish real-time election coverage.

## Collection and limitations

A new bounded batch selected 200 previously unvisited registered entry points in
Maine, Michigan and Ohio, the states with remaining distinct starts after the earlier
national batches. It made 250 HTTP attempts including redirects, recorded 212 targets,
and fetched 25 HTML pages; 187 targets failed. It discovered historical Ohio report
files and additional locality pages. This is a concentrated continuation, not a new
nationally representative sample. Failures remain failures, not absent jurisdictions.

Three linked Maryland pages were fetched separately with depth zero. The official
2026 election-data directory yielded 49 CSV leads within the 50-candidates-per-page
limit. A new catalog rule recognizes artifacts under an explicit year-specific election
data directory even when link labels are only party names. Script assets, sign-in
pages and sitemaps remain excluded. The catalog now has 248 successful target fetches,
667 targets not fetched and 25 failures. Successful targets can still be application shells.

Additional direct payload inspection fetched three already-linked Maryland/Wyoming
payloads, bounded to 10 MB each; these requests are separate from discovery counters.
Minnesota returned Radware bot challenges during six direct page probes. Those captures
remain local; their transient URLs and challenge metadata are not published. No CAPTCHA
was solved. Browser inspection of Idaho yielded no rendered vote totals.

## Payload verification

**Maryland:** the official 2026 gubernatorial primary HTML contains 11 candidate rows
with early, election-day, mail and provisional counts. The linked Democratic
congressional-district CSV contains 1,196 rows. The two statewide Democratic governor
candidates reconcile exactly across eight district columns and the HTML totals:
**633,080 votes**. County/local rows are kept separate from statewide rows.

`discovery_payloads.py` provides strict schema inspection and reconciliation; missing
counts, malformed or duplicate rows, candidate mismatch and inconsistent totals raise
errors. The observed HTML tables and a four-row CSV excerpt provide offline regression
fixtures. `inspect_maryland_discovery_payload.py` reproduces the cross-check from saved
files without network access. This validates one historical contest/party only; it
does not validate all 1,196 rows, county service, precinct completeness or November
2026 reporting.

**Wyoming:** the linked official 2026 primary ZIP downloaded successfully and contains
three readable workbooks: statewide summaries, county precinct results and county
precinct ballot totals. The workbooks identify August 18, 2026. The Albany sample
precinct's party counts add to its 772-ballot total. Workbook names, sheet inventories,
archive digest and sample counts are recorded; full ingestion and statewide reconciliation
remain future work.

`audit/dashboard-discovery/payload-inspection.json` records exact observed parent and
payload URLs, content digests, limited verification scope and distinct historical
inspection states. The source-lead catalog remains conservative: these checks do not
promote served jurisdictions or live coverage. **Verified live sources remain zero.**

## Validation and next iteration

399 local tests pass, including observed Maryland reconciliation, duplicate/missing-data
rejection, account/sitemap exclusion and Radware/CloudFront block detection. Focused lint
passes. The national enumeration audit retains 6,288 named units with no missing starting
points, while its coverage-complete flag remains false.

Next: implement ingestion of the observed Maryland precinct CSV schema and Wyoming
workbooks with cross-checks against official totals; resolve public-app shells through
observed assets or browser-rendered evidence; obtain authoritative service-area mappings;
and expand locality starts outside the MI/OH/ME-heavy registry. Historical payload access
must remain separate from an election-night update test. Draft PR #70 remains unmerged.
