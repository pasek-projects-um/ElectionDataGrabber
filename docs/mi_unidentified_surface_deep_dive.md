# Michigan unidentified-surface deep dive

The first top-10 fingerprint pass labeled several surfaces `unknown_web`. Manual inspection shows this bucket mixes at least three reusable source families and some crawler noise.

## Lenawee — electionlenawee.com

Not a live-result vendor shell. It is a dedicated election archive/site exposing recurring vendor-generated PDFs:
- ElectionSummaryReportRPT
- StatementOfVotesCastRPT
- Michigan Canvass Report
- occasional partial-canvass/certificate documents

The archive is organized cleanly by year back through at least 2008. Treat this as an authority/archive family whose downstream artifacts are standardized tabulator reports. The Statement of Votes Cast is the preferred precinct-level artifact.

## Schoolcraft — county-hosted report archive

The crawler followed an irrelevant jobs link, but the county has a dedicated Election Results section. It exposes both summary reports and explicit precinct-level Statements of Votes Cast. The 2024 summary includes:
- precincts reported (9 of 9)
- voters cast / registered voters
- counting-group labels including Election Day and Early Voting in the unofficial report

This is not an unknown platform problem; it is direct standardized report-PDF ingestion plus better navigation discovery.

## Alpena — CivicPlus + standardized report PDFs

CivicPlus is only the archive shell. The county publishes recurring precinct Statements of Votes Cast and summary PDFs. 2024 November Statement of Votes Cast has precinct, registered voters, voters cast, turnout, and contest results. Historical archive includes precinct-by-precinct reports.

## Clinton — CivicPlus Archive Center + canvass report PDFs

The useful source is the CivicPlus archive/document layer. Recent official canvass reports expose precinct-level contest results plus Election Day and Absentee ballots cast, registration, turnout, and precincts-reporting progress. This deserves a reusable canvass-report parser downstream of CivicPlus discovery.

## Newaygo historical downloads

Several `unknown_web` rows are actually PDFs/download wrappers whose payloads contain links to old HTML result systems. This suggests a legacy-static-results family rather than bespoke county parsing.

## Implication

The unknown bucket should be split into:
1. standardized tabulator report PDFs (ElectionSummaryReportRPT / StatementOfVotesCastRPT / Canvass Results Report);
2. CMS/archive discovery shells (CivicPlus/Jimdo/WordPress);
3. legacy static HTML election-report directories;
4. true unknown result applications.

Build the standardized report-PDF parser before inventing more county-specific adapters.
