# Local election source coverage tracker

The tracker separates three quantities:

- **known_units_with_source**: canonical local election units for which we have identified a usable authority/results source.
- **known_units_missing_source**: canonical units we know exist but for which we have established no usable local source yet.
- **estimated_unknown_units**: expected units not yet individually enumerated or adjudicated.

Invariant: `expected_primary_units = known_units_with_source + known_units_missing_source + estimated_unknown_units`.

`expected_primary_units` is a planning estimate, not ground truth. Replace it with authoritative enumeration as each state is completed. A failed crawl does not automatically make a unit known-missing; missing is an adjudicated state. Primary units are source authorities, not precinct/reporting units. Secondary municipal sources can be tracked separately where they coexist with county authorities.
