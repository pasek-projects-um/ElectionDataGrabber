# Election-night reporting topology

## Why this matters

Election-night results should not be modeled as a single scalar such as `percent_precincts_reporting`.
A geographic precinct return is often closer to present/absent, while absentee, early, provisional,
and other vote modes may arrive on different schedules and at different aggregation levels.

The system must preserve the topology through which votes are reported in real time.

## Distinguish unit presence from component completeness

For every reporting unit, track two separate concepts:

1. **Unit presence**: has this reporting unit appeared at all?
2. **Component completeness**: which vote-mode components appear absent, partial, complete, or unknown?

A precinct can therefore be present while absentee or early-vote components remain absent or aggregated elsewhere.

## Canonical vote-mode components

Initial normalized modes:

- election_day
- early_in_person
- absentee_mail
- provisional
- uocava
- other
- total

Always preserve the source's original label alongside the normalized mode.

## Aggregation scope

Every live result observation should record where the source says the votes are aggregated:

- precinct
- ward
- municipality
- county
- multi_precinct_avcb
- early_vote_center
- state
- unknown

The same numeric total means different things depending on aggregation scope.

## Allocation status

Where possible, classify how a result relates to geographic precincts:

- native_to_precinct
- reassigned_to_precinct
- aggregated_multi_precinct
- countywide
- synthetic_reporting_unit
- unknown

## Preserve two topologies

### Live reporting topology

The actual units and vote modes that arrive during election night.

Example:

```
                    ED      EARLY      ABSENTEE
Precinct 001        yes       ?            -
Precinct 002        yes       ?            -
Precinct 003        no        ?            -
AVCB 7               -        -         12,481
County Early Ctr     -      8,314           -
```

### Final geographic topology

The eventual allocation of votes to final precinct/geographic units after canvass or official reallocation.

These topologies must not be conflated. A jurisdiction may report absentee ballots through a central counting board on election night and later publish those votes by voter home precinct.

## Reporting-process priors

For modeling, each jurisdiction/election should accumulate a reporting-process history:

- typical ordering of vote-mode releases
- whether absentee/early votes are precinct-assigned or centrally aggregated
- number and identity of central reporting units
- usual lag between Election Day precincts and non-ED modes
- whether a precinct appearing implies only ED completeness or broader completeness
- whether mode totals are revised in place or appended as batches

These reporting-process priors should be modeled separately from partisan/turnout priors.

## Observation schema requirements

Every live observation should preserve at least:

- election_id
- source_id
- source_timestamp
- retrieval_timestamp
- reporting_unit_id
- geographic_scope
- aggregation_scope
- contest_id
- choice_id
- vote_mode
- raw_vote_mode
- votes
- ballots_observed if available
- registered_voters if available
- component_status: absent | partial | complete | unknown
- allocation_status
- source_status: unofficial | official | certified | unknown
- snapshot hash

## Priority strategy for early development

Over-index first on jurisdictions where the relationship between absentee/early votes and precinct totals is explicit and reconstructable.

High-value jurisdictions are those where we can answer questions like:

- Are Election Day votes precinct-native?
- Are early votes assigned back to home precincts or reported by early-vote center?
- Are absentee ballots assigned back to home precincts, reported by AVCB, or countywide?
- Does the final official file reallocate centrally reported modes back to precincts?
- Can we map live reporting units to final geographic precincts?

These jurisdictions provide clean training data for learning reporting topology. Once the system learns and validates these patterns, expand to jurisdictions with inconsistent or ambiguous aggregation.

## Suggested source-quality tiers for live-model training

### Tier A: explicit mode-to-precinct mapping

- precinct-native Election Day totals
- explicit early/absentee/provisional mode columns
- stable reporting-unit identifiers
- documented mapping between central units and final precincts when central aggregation exists
- archived election-night or timestamped updates preferred

### Tier B: partially explicit mapping

- precinct totals plus one or more centrally aggregated modes
- mapping can be reconstructed from official documentation or final files

### Tier C: ambiguous aggregation

- mode totals available, but their geographic relationship is unclear
- preserve observations, but exclude from early topology training unless reconciled

### Tier D: aggregate-only

- county/state totals without meaningful precinct reporting units
- useful for constraints and validation, not for precinct-level topology training

## Reconciliation across aggregation levels

Use overlapping aggregate totals as constraints when geography or mode allocation is unclear:

- precinct -> ward
- ward -> municipality
- municipality -> county
- precinct -> legislative district
- precinct -> congressional district
- vote modes -> total
- party-primary ballots -> total party ballots

If lower-level units fail to reconcile while a higher-level total does reconcile, that pattern is evidence about where reporting or boundary changes occurred.

## Uncertainty

Keep four classes separate:

- observed: exactly what the source reported
- derived: deterministic transformation of source data
- imputed: inferred missing quantity
- modeled: statistical estimate

Do not assign modeled uncertainty to exact source observations merely because downstream allocations are uncertain. Preserve uncertainty components for spatial allocation, temporal crosswalks, ACS sampling error, and reporting-process inference separately.
