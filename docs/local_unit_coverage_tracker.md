# Local election source coverage tracker

The tracker separates **enumeration** from **source capability**.

Each expected primary local unit must be in exactly one mutually exclusive accounting bucket:

- **enumerated_unresolved**: the canonical unit has been individually identified, but source capability has not yet been adjudicated.
- **known_final_only**: historical/final/certified source established; election-night source not established.
- **known_election_night_only**: election-night source established; durable historical/final source not established.
- **known_both**: both source classes established.
- **known_units_missing_source**: canonical unit is known and sufficiently investigated, but neither useful source class is established.
- **estimated_unknown_units**: expected units not yet individually enumerated.

Derived metrics:

`enumerated = enumerated_unresolved + known_final_only + known_election_night_only + known_both + known_units_missing_source`

`known_units_with_any_source = known_final_only + known_election_night_only + known_both`

`known_units_with_final = known_final_only + known_both`

`known_units_with_election_night = known_election_night_only + known_both`

Hard invariant:

`expected_primary_units = enumerated + estimated_unknown_units`

The updater and tests enforce this arithmetic. Counts cannot be negative.

## Transition rules

Discovery does not itself establish a canonical unit. After reconciliation to a canonical jurisdiction ID, a unit moves from **estimated_unknown** to **enumerated_unresolved**. Evidence review then moves it into exactly one capability/missing bucket.

A failed crawl never creates **known_missing_source**. A certified file never implies election-night capability, and an election-night application never implies durable historical/final capability.

Primary units are source authorities, not precinct/reporting units. Raw discovery observations remain evidence and must not be counted as jurisdictions until reconciled.
