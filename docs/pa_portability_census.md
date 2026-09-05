# Pennsylvania statewide portability pass

Pennsylvania is the control state after Maine and Connecticut.

## Strategy

1. Start with the Pennsylvania Department of State bulk/official result layer.
2. Census all 67 county election authorities in parallel.
3. Prefer state bulk precinct data for historical normalization and reconciliation.
4. Probe county systems for election-night/live feeds, richer precinct detail, turnout, vote mode, ballot order, and local contests.
5. Preserve raw artifacts and distinguish source result order from authoritative ballot order.
6. Classify county systems A-E using the same portability rubric as Ohio.

The goal is a one-pass statewide inventory, not a hand-written parser per county.
