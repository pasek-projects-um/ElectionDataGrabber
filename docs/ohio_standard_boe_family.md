# Ohio standardized BOE family

A large share of Ohio county BOE sites use the Ohio Secretary of State-hosted pattern:

- `https://www.boe.ohio.gov/{county}/election-info/election-results/`
- recurring links named `Cumulative Results`, `Precinct Detail`, and often `Overlap Results`
- standardized precinct/polling lookup at `https://lookup.boe.ohio.gov/vtrapp/{county}/precandpoll.aspx`

Observed 2024 precinct-detail reports are often PDFs rather than HTML. Athens' report is
Electionware-generated; Greene's report uses a Statement-of-Votes-Cast style. Both expose
precinct turnout/registration and candidate totals.

## Important ballot-order rule

Results-column order is not automatically voter-facing ballot order. Ohio rotation makes this
especially important. ElectionDataGrabber stores artifact order in `source_order` and only
populates `ballot_order` when a ballot, rotation, or other authoritative precinct-level source
actually establishes voter-facing order.

## Adapter strategy

1. Discover report URLs from the standardized BOE archive page.
2. Store the raw PDF unchanged.
3. Extract structured PDF text/tables with a generic report extractor.
4. Normalize precinct turnout and contest totals.
5. Join precinct/polling CSV separately for current precinct names, polling locations and district assignments.
6. Join ballot/rotation records separately when available.

The archive-page discovery layer is already reusable across counties; PDF table extraction is
the next generic family to harden.
