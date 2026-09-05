# Jurisdiction and precinct coverage model

ElectionDataGrabber uses two separate registries.

## 1. Administrative jurisdiction backbone

The national county registry is sourced from the U.S. Census Gazetteer and keyed by GEOID.
It enumerates counties and county-equivalents before any election-result discovery begins.

Recommended hierarchy:

- state / territory
- county or county-equivalent
- county subdivision / municipality where relevant
- election authority
- source endpoint(s)

The Census layer is authoritative for general-purpose geography, not for election administration.

## 2. Observed election reporting units

Precincts, wards, AVCBs, early-vote centers, consolidated precincts, and other reporting units
are recorded exactly as observed in a specific source for a specific election.

Never assume:

- the same precinct label means the same geography across elections;
- a Census VTD equals a current election precinct;
- a polling place is the same thing as a reporting precinct;
- an absentee counting board is geographically equivalent to the precincts whose ballots it counts.

Each observed unit therefore retains:

- source ID
- election ID
- state and county
- raw label
- inferred unit type
- eventual canonical reporting-unit ID
- eventual geometry ID
- provenance for the source artifact

## National precinct-discovery ladder

For each county/county-equivalent, attempt in this order:

1. Official state election-result export with precinct-level records.
2. Official county/local election-result export or live reporting system.
3. Official GIS/open-data precinct layer.
4. Historical official result files.
5. MEDSL precinct datasets as an independent historical reference.
6. OpenElections normalized/source repositories as a historical reference and discovery aid.
7. Census Voting District (VTD) geography as a reference-only geographic baseline.

The registry should track both **observed precinct labels** and **verified current election precincts**.
They are not interchangeable.

## Coverage states

A county can independently have:

- county_identified
- authority_identified
- historical_results_found
- precinct_labels_observed
- precinct_geometry_found
- current_precinct_list_verified
- live_results_source_found
- live_source_parsed
- vote_mode_detail_found
- ballot_order_found
- polling_location_data_found

This lets national progress be measured without pretending that every county has the same depth of coverage.
