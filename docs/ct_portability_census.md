# Connecticut election-results portability census

Connecticut is a deliberate stress test for the geography and authority model.

## Why Connecticut

- Election administration is town/municipality centered rather than county-authority centered.
- The eight historical counties are still meaningful for older election/geographic data, but Census county-equivalent geography changed in 2022 to nine planning regions/COGs.
- Results ingestion therefore needs election-time authority topology and geography-vintage topology to remain separate.

## Core rules

1. Treat towns/cities as the primary authority/discovery unit unless a state source is more authoritative for a specific election artifact.
2. Preserve historical county identifiers with validity dates; never overwrite them with current planning-region codes.
3. Add planning-region county equivalents as a later geography layer, not as retroactive replacements for historical election records.
4. Reconcile town -> planning region / historical county (as appropriate for the election vintage) -> state only where the geography relationship is valid.
5. Preserve wards, voting districts, precincts and reporting units below town level where sources expose them.

## Portability classes

A = existing parser works unchanged
B = existing parser works with source profile/config only
C = reusable generic enhancement
D = genuinely new platform family
E = bespoke/unstructured

## Initial objective

Seed a mixed cohort of large cities, suburban towns, small towns and geographically awkward cases. Reuse the Maine municipality-first topology and Ohio/Michigan archive/PDF extraction before writing Connecticut-specific parsing code.
