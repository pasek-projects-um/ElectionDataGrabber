# Cross-state semantic edge cases

These are schema/model requirements, not merely parser quirks.

## North Dakota: no voter registration

North Dakota does not require voter registration. Do not assume a registered-voter denominator exists for turnout models or reporting-unit metadata.

Represent registration denominator as nullable with an explicit reason/status, e.g.:
- registered_voters: null
- registration_system: none
- turnout_denominator_type: eligible_population / ballots_cast_only / other official denominator

Never coerce missing registration into zero.

## Minnesota: DFL identity

Minnesota's Democratic-Farmer-Labor Party (DFL) must be represented as the state party organization/ballot label while retaining its relationship to the national Democratic Party.

Party identity therefore needs at least:
- party_id (stable canonical entity)
- ballot_party_label
- state_affiliate
- national_party_family

Do not normalize the literal DFL ballot label away at ingestion.

## New York: fusion voting

A candidate may appear on multiple party/independent ballot lines. Candidate identity, nomination/party line, ballot position, and votes must be separate dimensions.

Canonical relationship:

candidate
  -> candidacy/contest
     -> one or more ballot lines
        -> party/independent body
        -> ballot position
        -> votes at reporting unit

Preserve line-level votes even when downstream products also expose candidate-combined totals. Never treat the same candidate on two lines as two different candidates merely because party labels differ.

These requirements should propagate into historical normalization, election-night ingestion, reconciliation, and statistical modeling.
