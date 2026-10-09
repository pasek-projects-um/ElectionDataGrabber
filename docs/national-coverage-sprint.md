# National starting-point coverage sprint

Tracking issue: https://github.com/pasek-projects-um/ElectionDataGrabber/issues/67

**Only active feature goal:** enumerate every election-administration/reporting unit in the United States and supply at least one credible discovery starting URL per unit. Preserve alternative URLs when jurisdiction ownership is ambiguous.

Do **not** count the existing 757-unit registry as the full national denominator. Never count a state-directory fallback as a verified local official site. Keep separate coverage metrics for any-start, direct/shared source and verified reachable.

Work state by state, reconciling jurisdiction identifiers, authoritative parent relationships, and source provenance. Keep URL inventory CI deterministic and fast; use manual crawls for evidence gathering. Defer local model classification, deployment, additional ingestion adapters and unrelated features until the nationwide any-start metric genuinely reaches 100%.

## Internet Archive escalation for uncertain starts

When a jurisdiction has only a state-directory fallback, generic government homepage,
unreachable or ambiguous election-office page, or multiple competing candidate URLs,
search the Wayback Machine for its election-site link structure. Restrict queries to
the 2024 November 5 general election window, jurisdiction-specific 2025 election dates,
and jurisdiction-specific 2026 primary dates. Dates must be supplied explicitly; never
assume every jurisdiction has the same 2025 election or 2026 primary date.

Use `scripts/wayback_starting_point_leads.py --targets targets.csv` with columns
`jurisdiction_id,seed_url,election_type,election_date`. The script produces archived-only
candidate links and their snapshot timestamps, and is deliberately **manual**, not PR CI.
Archive evidence must not be treated as proof of current reachability or official status.
Promote an archive lead to a verified current start only after a separate live check and
authority/jurisdiction confirmation. Record original and archived URLs together.

Prioritize these archive lookups over speculative general web searching for uncertain units.


## High-yield coverage pass (October 2026)

**Prioritization correction:** finish straightforward election-authority units and their starting URLs before tackling large, fragmented municipal/town topologies. The near-term priority is high-confidence coverage of consequential election reporting jurisdictions, not maximum raw unit count. This is prioritization, **not** a redefinition of the nationwide denominator or a claim of 100% coverage.

First clear small and tractable remaining gaps: DC (1), AK (1, state-administered model), HI (4), RI (39), and MN (87), then tackle IL (108) and MO (116) by enumerating their separate election authorities. Where possible, reuse official state directories and retain distinct source URLs/provenance. Avoid treating Census geography as automatically equivalent to an election-administration authority.

Defer the most fragmented rosters from this **pass**: NH (234), VT (247), MA (351), WI (1,850). They remain active gaps, not covered by assumption or removed from the denominator. Revisit based on available bandwidth and election competitiveness/contested district relevance; do not claim every election in a state is uncompetitive.

Repair shared-core derived-tracker consistency and restore passing CI before merging expansion. Run Wayback date-bounded lookups only for ambiguous links in the states currently being addressed. Report newly named units, direct verified leads, fallback-only units, provisional-denominator status, and explicitly deferred gaps separately.
