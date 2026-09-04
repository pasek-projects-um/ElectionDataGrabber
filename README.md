# ElectionDataGrabber

ElectionDataGrabber is an experimental pipeline for discovering, snapshotting, normalizing, and diffing U.S. local election-result sources, with Michigan as the initial test bed.

## Design principles

1. Prefer official structured data over rendered pages whenever available.
2. Save immutable raw snapshots before parsing or normalization.
3. Keep source timestamps and fetch timestamps separately.
4. Treat precinct/reporting-unit identity as election-specific until a crosswalk proves continuity.
5. Preserve vote-mode detail instead of collapsing it into totals.
6. Keep official sources, open-data mirrors, and media sources distinct in provenance.
7. Build platform adapters (Clarity/ENR, county systems, archives) rather than one scraper per county.

## Initial Michigan benchmark

OpenElections currently publishes 2024 general-election precinct CSV files for all 83 Michigan counties. The script below inventories those files, counts distinct county-scoped precinct labels, records row counts, and detects vote-mode columns.

```bash
python scripts/bootstrap_mi_openelections.py
```

The OpenElections files are used as a historical benchmark/fallback source, not as the canonical live authority.

## Current structure

```text
registry/                       source registry and inventories
scripts/                        acquisition/bootstrap utilities
src/election_data_grabber/
  adapters/base.py              fetch + immutable raw snapshots + adapter contract
  discovery.py                  result-link discovery and vendor fingerprints
  models.py                     canonical source/snapshot/result models
```

## Reusable upstream work

We intend to reuse compatible open-source tooling rather than reimplement vendor protocols. In particular, OpenElections' `clarify` library (MIT licensed) can discover and parse structured XML/CSV/XLS reports from Clarity election-result systems. MEDSL's precinct datasets and OpenElections' normalized state repositories are useful as independent historical reference datasets and QA targets.

## Near-term roadmap

- Inventory all 83 Michigan county authority/result URLs and fingerprint their reporting platforms.
- Implement Washtenaw live-result parsing using the county's current election-reporting pages.
- Add Clarity/ENR support through `clarify`.
- Add change detection that emits result deltas only when a source snapshot changes.
- Add QA checks for candidate totals, vote-mode totals, turnout, duplicate rows, and precinct completeness.
- Build election-specific reporting-unit registries, then crosswalk precincts across elections.
