# Maine election-results portability census

Maine is deliberately treated as a **municipality-first** state for election-result ingestion.
County is retained as geography, but the primary reporting/administrative unit can be a city,
town, plantation, or other municipality.

## Goals

1. Inventory the Maine Secretary of State statewide results products.
2. Inventory municipality-level result sources, beginning with the largest municipalities and
   a rural/small-town sample.
3. Preserve ward/precinct distinctions where municipalities expose them.
4. Record whether absentee/early-style votes are allocated to local reporting units or only
   available at broader aggregation.
5. Test Michigan/Ohio parser portability before adding Maine-specific code.

## Portability classes

A = existing parser unchanged
B = source profile/configuration only
C = reusable generic enhancement
D = genuinely new source family
E = bespoke/unstructured

## Important geography rule

Do not assume Maine counties are equivalent to Michigan or Ohio county election authorities.
The canonical registry must permit:

state -> county -> municipality -> ward/precinct/reporting unit

with election-specific reporting topology.
