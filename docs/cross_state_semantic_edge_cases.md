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

## Louisiana: open/jungle primaries and runoffs

Louisiana election stages must be represented explicitly. A "primary" can be an all-candidate contest in which candidates from multiple parties compete together, with a later runoff/general stage if no candidate satisfies the governing threshold.

Do not infer nomination semantics from the word primary.

Preserve at least:
- election_stage: primary / runoff / general / special / other
- nomination_system: top_two / majority_runoff / partisan_nomination / nonpartisan / other
- threshold_rule: majority / plurality / top_n / statutory special rule
- advances_to_election_id
- predecessor_election_id
- candidacy_id stable across stages where the same candidate advances
- party/ballot label at each stage
- contest continuity identifier linking primary and runoff versions of the same office

A runoff should not be ingested as an unrelated contest merely because it occurs on a later election date.

For election-night modeling, preserve the condition that determines whether a runoff is triggered and whether the result is mathematically clinched under the applicable threshold rule.
