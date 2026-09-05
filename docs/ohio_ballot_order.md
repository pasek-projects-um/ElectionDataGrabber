# Ohio ballot-order semantics

Ohio requires special care because candidate order can rotate across precincts.
ElectionDataGrabber therefore treats ballot order as a property of the
**reporting-unit observation** whenever the source exposes order at that level.

Rules:

1. Never infer precinct candidate order from a countywide summary.
2. Preserve source row/order within every precinct-contest block.
3. Set `ResultObservation.ballot_order_scope="reporting_unit"` for such data.
4. A `ContestChoice.ballot_order` value is only a default/global order and must
   not overwrite reporting-unit order.
5. Historical exports that omit order should leave it unknown rather than
   reconstructing it from candidate name, party, or county totals.

This is analytically useful as well as a parsing requirement: candidate rotation
can be modeled directly when estimating ballot-position effects.
