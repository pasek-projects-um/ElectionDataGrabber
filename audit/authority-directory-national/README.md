# National discovery readiness, October 10, 2026

| Category | Named units | Meaning |
| --- | ---: | --- |
| Observed result-page candidate | 39 | A fetched catalog candidate joined through a local hunting URL; inspect its payload and service area. |
| Evidence-backed hunting location | 248 | An existing local starting URL or unique directory website/result clue; follow and review it. |
| Unresolved location | 6,001 | No local clue established by these evidence layers yet. |

These are discovery categories, not verified live feeds. Unit counts do not count
distinct pages. Directory-label and catalog-parent associations remain provisional.
State fallback pages do not establish local coverage, and inaccessible pages do
not establish that a source is absent.

- `unit-readiness.csv`: every named unit, category, hunting/result URLs and next action.
- `directory-link-candidates.csv`: 1,420 observed links with roles, parent URLs,
  bounded excerpts, capture hashes and provisional unit matches.
- `capture-status-by-state.csv`: all 51 state/DC starts; 29 usable captures,
  12 robots-denied, four robots-unresolved and six fetch-unresolved.
- `discovery-priorities.csv`: states ranked by unresolved named units, with an
  initial lane based on whether an official page capture is available.
- `summary.json`: machine-readable counts and limitations.

The first pass used 96 bounded HTTP requests. Offline replay made zero requests.
Raw captures are retained in the worker's snapshot directory, outside this report.
Registry denominators retain their existing provisional/confidence statuses.

## How to increase useful clues

1. Inspect already captured state pages for links to deeper local-office
   directories, structured data, embedded directories and downloadable lists.
   A statewide landing page with no county labels is a starting point for another
   layer, not a failed locality search. Review Maryland's 24 and Idaho's 44 unique
   directory-label clues first to validate the extraction patterns.
2. Prioritize large unresolved denominators: Wisconsin, Massachusetts, Maine,
   Texas, Vermont, New Hampshire and Connecticut. Accessible captures and
   inaccessible starts need different follow-up paths; consult the priority CSV.
3. For inaccessible starts, locate alternate official links and downloadable
   directories; use historical official pages or Internet Archive captures as
   dated clues. Preserve access failures and do not bypass robots restrictions.
4. After reviewing local authority associations, feed accepted local starts into
   the watcher. Follow current and historical result links, retain platform/URL
   signatures and distinguish past-election endpoints from current candidates.
5. Move a unit between categories only with recorded evidence. Verify election
   context, service area and actual result updates before claiming live coverage.

Replay instructions are in `docs/authority-directory-frontier.md`. No recurring
worker has been deployed by this report.
