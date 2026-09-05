# Maine micro-geography probe

The ingestion target is the **smallest election reporting unit actually published for a given election**, not a fixed notion of precinct.

## Resolution ladder

1. statewide
2. county (geographic/reconciliation key; often not Maine's reporting authority)
3. municipality / plantation
4. ward or district
5. precinct
6. reporting unit
7. subunit

A source may skip levels. We preserve the publisher's native labels and parent relationships rather than forcing every row into county -> precinct.

## What to capture at the floor

For each result row, retain where available:

- municipality / plantation
- ward, district, precinct and subunit labels
- contest
- candidate / choice
- candidate source order
- verified ballot position only when an authoritative ballot source supports it
- vote total
- registered voters
- ballots cast / turnout
- election-day, absentee, early or other vote-mode split
- source artifact and page/table coordinates
- extraction confidence and warnings

## Maine-specific experiment

Large municipalities may expose wards/precincts while many small towns collapse directly to one municipal reporting unit. Plantations and unorganized-territory reporting can be smaller geographically but administratively different. Therefore resolution is election/source-specific.

The statewide SOS municipality totals should be treated as reconciliation constraints. Local submunicipal rows sum upward where semantics permit; residuals are retained explicitly rather than silently redistributed.

## Next validation target

Probe representative high-resolution municipalities (Portland, Lewiston, Bangor, Augusta) alongside tiny towns, islands, plantations, and unorganized-territory products. Record the minimum native reporting unit and whether absentee/early votes are allocable to it.
