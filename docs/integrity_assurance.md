# Integrity assurance: affirmative evidence of consistency

ElectionDataGrabber should not be designed only to identify anomalies. It should also be able to produce strong, auditable statements that **no material anomaly is evident in the data we can observe**.

The system must never equate "not flagged" with "proved correct." Instead it should distinguish among:

- **unexamined** — insufficient data or checks have been run;
- **insufficient evidence** — data exist, but important reconciliation/audit dimensions are missing;
- **consistent within observed evidence** — available checks reconcile within expected tolerances;
- **strongly supported** — multiple independent evidence layers reconcile and known administrative changes explain observed discontinuities;
- **requires follow-up** — one or more material discrepancies remain unresolved.

## Affirmative assurance packet

For a jurisdiction/election, the system should report which evidence classes were available and passed:

1. **Source integrity and provenance**
   - raw snapshots preserved;
   - cryptographic hashes recorded;
   - source timestamps and retrieval timestamps retained;
   - revision history reconstructable;
   - independent source copies agree where available.

2. **Arithmetic and aggregation reconciliation**
   - candidate totals reconcile from precinct/reporting units to higher aggregates;
   - vote-mode totals reconcile to combined totals where definitions permit;
   - precinct/ward/municipality/county aggregation constraints reconcile;
   - ballots cast, contest votes, undervotes, overvotes, invalid votes, and write-ins reconcile under the jurisdiction's published definitions;
   - partisan primary ballot totals reconcile where available.

3. **Reporting topology consistency**
   - election-day, early, absentee/mail, provisional, and other components appear in expected reporting units;
   - aggregation scopes are understood or explicitly marked unknown;
   - update order, batch size, and revision behavior are consistent with the jurisdiction's reporting regime or explained by documented changes.

4. **Geographic consistency**
   - reporting units map to election-vintage precinct/ward/municipal geometry where available;
   - precinct splits/merges and district changes are represented explicitly;
   - residual aggregation discrepancies are not being hidden by a bad crosswalk;
   - historical comparison uses compatible or uncertainty-propagated geographic units.

5. **Administrative-regime consistency**
   - known law, procedure, vendor, and tabulation changes are represented as regime breakpoints;
   - historical pooling is limited when regimes differ;
   - apparent discontinuities explained by documented rule/process changes are not mislabeled as anomalies.

6. **Statistical consistency**
   - observed results are evaluated against local and hierarchical predictive distributions;
   - no-pooling, weak-pooling, and hierarchical comparators are retained;
   - unusually large residuals, pooling conflict, mode shifts, or structural breaks are surfaced;
   - absence of material residuals is recorded when the test had sufficient power to detect discrepancies of practical concern.

7. **Post-election verification**
   - canvass adjustments are captured;
   - certification status is recorded;
   - recounts and audit results are linked where available;
   - ballot-comparison / risk-limiting audit evidence is incorporated where available;
   - final reported totals are checked against later official artifacts.

## Assurance must be power-aware

A statement that no anomaly is evident is only meaningful if the available data had enough statistical and administrative power to detect one.

For every check, retain:

- the discrepancy type being tested;
- the smallest practically important discrepancy the check could reliably detect;
- the evidence actually available;
- the uncertainty and missingness affecting the check;
- whether the test passed, failed, or was underpowered.

Example:

```text
Absentee-to-precinct allocation:
  evidence: precinct-native final allocation + county absentee batch totals
  detectable discrepancy: ~0.5% of absentee ballots at county level
  observed residual: 0.03%
  status: strongly consistent
```

is far more meaningful than:

```text
No anomaly detected.
```

## Independent evidence is more valuable than repeated versions of the same evidence

Confidence should rise most when different evidence-generating processes agree:

- live result feed;
- official precinct export;
- canvass report;
- certified totals;
- ballot manifest;
- cast-vote records;
- audit/recount evidence;
- geographic and administrative records.

Repeatedly observing the same vendor feed should not be treated as equivalent to independent corroboration.

## Proposed assurance output

Each jurisdiction/election should eventually produce an object like:

```json
{
  "status": "consistent_with_observed_evidence",
  "evidence_coverage": {
    "source_provenance": "strong",
    "aggregation_reconciliation": "strong",
    "reporting_topology": "strong",
    "geographic_reconciliation": "moderate",
    "administrative_regime": "strong",
    "statistical_power": "strong",
    "post_election_audit": "unavailable"
  },
  "material_unresolved_discrepancies": 0,
  "underpowered_checks": ["paper_ballot_audit"],
  "notes": [
    "No material inconsistency found among available independent evidence layers.",
    "This is not a proof of absence of all possible error or misconduct."
  ]
}
```

## Public-facing language

Prefer precise language such as:

- "No material inconsistency was detected in the available evidence."
- "Precinct, mode, and county totals reconcile within the published accounting rules."
- "Observed reporting behavior is consistent with the documented administrative regime."
- "The available data were sufficient to detect discrepancies larger than X at this aggregation level."

Avoid claims such as:

- "This election was definitely clean."
- "Fraud is impossible."
- "No anomaly exists."

The objective is to make reassuring evidence as visible and auditable as suspicious evidence, while preserving the distinction between strong consistency and proof of absence.
