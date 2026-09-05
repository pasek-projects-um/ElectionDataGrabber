# Local election source coverage tracker

The tracker separates source discovery from source capability.

For each state's primary local units:

- **known_final_only**: a usable historical/final/certified-results source is known, but no usable election-night source is yet known.
- **known_election_night_only**: a usable election-night source is known, but we have not established a durable historical/final source.
- **known_both**: both election-night and historical/final result sources are known for the unit.
- **known_units_missing_source**: the canonical unit is known to exist, but neither useful source class has been established after investigation.
- **estimated_unknown_units**: expected primary units not yet individually enumerated/adjudicated.

Derived totals:

`known_units_with_any_source = known_final_only + known_election_night_only + known_both`

`known_units_with_final = known_final_only + known_both`

`known_units_with_election_night = known_election_night_only + known_both`

Planning invariant:

`expected_primary_units = known_final_only + known_election_night_only + known_both + known_units_missing_source + estimated_unknown_units`

A failed crawl does not make a unit known-missing. Likewise, a certified precinct PDF does not imply election-night precinct reporting, and an election-night application does not imply that its historical files remain durably available.

Primary units are source authorities, not precinct/reporting units. Secondary municipal sources may be tracked separately where they coexist with county authorities.
