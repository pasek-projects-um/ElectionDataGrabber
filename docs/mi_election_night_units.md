# Michigan election-night reporting-unit census

Election-night reporting is source-specific and election-specific. County and municipal sources may coexist and expose different resolution or vote-mode detail.

For each election/source pair record:
- whether election-night results are available;
- the smallest identifiable election-night reporting unit;
- whether unit IDs are observable;
- what "reporting progress" means;
- whether completion is observable for an individual unit;
- vote-mode detail at that unit;
- whether updates are cumulative and timestamped;
- the certified reporting-unit floor;
- how election-night units crosswalk to certified returns.

Do not infer election-night resolution from certified historical precinct data.

Michigan's Secretary of State explicitly directs users to county election sites for updated unofficial results, while noting that local city/township clerk sites may also carry election information. This means discovery must search both county and municipal layers rather than selecting one authority level globally.

Ann Arbor is a concrete example: the city documents precinct-result transmission and AVCB reporting behavior while directing live-result users to Washtenaw County. The same election therefore has useful municipal process metadata and a county publication surface.
