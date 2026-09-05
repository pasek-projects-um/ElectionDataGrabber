# Michigan county platform census

Goal: enumerate all 83 Michigan counties before optimizing adapters.

The census output has one or more candidate result sources per county and records:
Census GEOID, county, official authority URL, discovered result URL, link label,
platform fingerprint, discovery status, and fetch errors.

## Workflow

1. Build `registry/us_counties_2025.csv`.
2. Expand `registry/mi_county_authorities.csv` until all 83 counties have an official authority URL.
3. Run `python scripts/mi_county_platform_census.py`.
4. Manually verify unknown fingerprints and add reusable signatures to `discovery.py`.
5. Rank adapter work by counties unlocked and by quality of precinct/mode detail.

Do not equate county geography with election reporting topology. A county may expose
municipal, precinct, consolidated, AVCB, early-vote-center, or countywide units.
