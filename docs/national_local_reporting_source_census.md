# National local reporting-source census

This branch is deliberately discovery-first. It inventories official local election-reporting surfaces without assuming that the county (or county-equivalent) is the only relevant authority.

## Search hierarchy

For every state, enumerate the legally/administratively relevant election authorities, then search:
1. state election authority / official local-authority directory;
2. county or county-equivalent election authority;
3. municipality, township, city, borough, parish, independent city, election district, or other local authority where state law/practice makes it relevant;
4. official election-night/result vendor links exposed by those authorities.

## Preserve separately
- authority URL vs result URL;
- source scope;
- whether it appears to publish election-night returns;
- smallest observed reporting geography;
- vote-mode detail;
- vendor/platform fingerprint;
- discovery provenance and verification status.

Do not infer that final/certified precinct returns imply precinct-identifiable election-night reporting.

## Initial expansion states

Prioritize states that broaden administrative topology and vendor diversity:
- Wisconsin — municipal clerks + county canvass/reporting
- Minnesota — strong state results backbone plus county/local cross-checks
- Massachusetts — municipalities are central reporting authorities
- Rhode Island — state/municipal structure, compact full census
- Vermont — town-level election administration, compact but heterogeneous
- New Hampshire — town/ward reporting, strong local relevance
- New Jersey — county election-night sources plus municipality/election-district detail
- Virginia — independent cities + counties
- Louisiana — parish model
- Alaska — non-county election geography/control case
- Maryland — county/independent Baltimore structure
- Missouri — local election authorities that do not map cleanly to county-only assumptions

The objective is not bespoke parsing on this branch. It is to learn the national source topology and produce verified candidate endpoints that downstream platform-family adapters can consume.
