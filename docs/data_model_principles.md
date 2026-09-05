# Data model principles

## Preserve raw source truth first

Every acquisition begins with an immutable raw snapshot. Normalization never overwrites source data.

Each normalized or derived record must retain enough provenance to trace back to:

- source ID and URL
- election ID
- source timestamp, if supplied
- retrieval timestamp
- raw snapshot hash
- parser version
- source-specific labels and identifiers

## Geography is temporal

Do not use current county, precinct, ward, or district identifiers as timeless primary keys.

Store election-vintage geography and relationships explicitly. This is necessary for cases such as Connecticut's recent county-equivalent changes and for routine precinct, ward, legislative-district, and congressional-district changes.

Preferred geography hierarchy is not a rigid tree. Election units can participate in multiple overlapping partitions:

- state
- county / county-equivalent
- municipality / township / county subdivision
- ward
- precinct
- consolidated precinct
- AVCB / absentee counting board
- early-vote reporting unit
- legislative district
- congressional district
- polling place

## Geometry-first where possible

Prefer authoritative election-vintage precinct shapefiles or GeoJSON when available.

Source preference:

1. official election-authority precinct geometry
2. official state/local GIS precinct geometry
3. election-vintage redistricting or VTD geometry
4. reconstructed geometry from blocks/crosswalks
5. name-only reporting units

Census VTDs are a reference layer, not an assumption that the VTD equals the operational precinct used in a given election.

## Census blocks as a common spatial substrate

Where geometry permits, use Census blocks or block pieces as the finest common crosswalk substrate rather than block groups.

Block groups often cut across precincts and precincts often cut across block groups. ACS block-group estimates should therefore be allocated with variable-appropriate weights and with uncertainty preserved.

Possible weighting bases include:

- population
- voting-age population
- CVAP
- housing units
- households
- registered voters
- area only as a weak fallback

## Geographic lineage graph

Represent changes between election-vintage units as typed relationships:

- same
- renamed
- split
- merge
- partial_transfer
- consolidated_for_reporting
- avcb_assignment
- early_vote_assignment
- unknown_overlap

Each relationship should retain evidence rather than only a single opaque confidence score. Evidence can include:

- polygon overlap
- Census-block overlap
- municipality/ward containment
- district membership
- polling-place continuity
- registered-voter totals
- turnout/ballot totals
- aggregate-result reconciliation
- normalized-name similarity

## Multiple aggregation levels are constraints

Preserve every useful aggregation rather than discarding higher-level totals after precinct data are obtained.

Examples:

- precinct -> ward
- precinct -> municipality
- ward -> municipality
- municipality -> county
- precinct -> state-house district
- precinct -> state-senate district
- precinct -> congressional district
- vote modes -> all-mode total
- partisan-primary ballots -> party ballot total

Differences in which aggregation levels reconcile across elections can help identify splits, merges, transfers, or changed reporting structures.

## Candidate and ballot structure

Where available, preserve:

- candidate/choice ballot order
- contest ballot order
- party
- incumbent status when explicitly supplied
- write-in status
- raw candidate/choice labels
- rejected/unassigned write-ins
- undervotes
- overvotes
- invalid votes
- straight-party totals where applicable

Never alphabetize away source ballot order.

## Reporting-unit metadata

Where available, preserve:

- precinct/reporting-unit source ID
- raw name
- normalized municipality
- ward
- precinct number/name
- polling-place name and address
- coordinates
- registered voters
- ballots issued/cast
- voting equipment or machine identifiers
- consolidated-precinct relationships
- early-vote-center assignments
- AVCB assignments

A geographic precinct, a reporting unit, and a polling location are different entities and must not be conflated.

## Uncertainty and provenance

Maintain a hard distinction among:

- OBSERVED: exactly what a source reported
- DERIVED: deterministic transformation of observed/source data
- IMPUTED: missing quantity inferred from other information
- MODELED: statistical estimate

For derived small-area quantities, preserve uncertainty components separately where possible:

- source sampling error / ACS margin of error
- spatial allocation error
- geographic-match uncertainty
- temporal-crosswalk uncertainty
- reporting-process uncertainty

Empirical Bayes or other partial-pooling methods should operate on these reliability differences rather than treating all precinct estimates equally. Preserve both raw and shrunken estimates, with shrinkage diagnostics.
