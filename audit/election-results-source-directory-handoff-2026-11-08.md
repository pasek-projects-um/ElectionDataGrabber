# Election-results source directory handoff — 2026-11-08

This repository's durable source of truth is the checked-in registry and audit input ledgers, not the expiring GitHub Actions artifacts. The source directory is reproducible using `python scripts/build_national_where_to_look.py` and `python -m scripts.audit_national_starting_point_coverage` on main. PR #80 was merged (f116caaf47d37dcc96f857f75e756f343db31b24) and includes `registry/local_site_discovery_leads.csv` in the directory. **No row count is proof of live feed verification.**

## Verified inventory snapshot

The November 8, 2026 successful [National where-to-look inventory run](https://github.com/pasek-projects-um/ElectionDataGrabber/actions/runs/42475562385) generated:
- `national-where-to-look.csv` (12,462 URL/role rows; 8,253 observed local-site candidates);
- `national-where-to-look-gaps.csv` (3,291 fallback-only localities);
- `national-where-to-look-summary.json` and national starting-point audit (6,288 enumerated localities, 2,997 direct-lead localities, 3,291 state-directory fallback only).

The [latest inspected watcher run](https://github.com/pasek-projects-um/ElectionDataGrabber/actions/runs/42534003989) succeeded on November 8 and reported 78,064 retained candidates, 18,156 due pages, 27 quarantined lead rows, and **zero newly verified live feeds in that run**. Its artifact contains `last-run.json`, `quarantined-local-site-leads.csv`, `jurisdiction-discovery-status.csv`, the candidate queue, and the checkpoint evidence tarball. The 287 MB expanded checkpoint is not checked into Git; the original Actions artifact is retained subject to expiration. This handoff does **not** certify checkpoint long-term preservation.

The [Maine end-to-end portability audit run](https://github.com/pasek-projects-um/ElectionDataGrabber/actions/runs/42458706580) succeeded. Shard 0 of 7 reported 50 localities, 8 unverified discovered sources, 5 artifacts found, 0 historically verified sources and 0 currently reachable verified sources. These are **shard** figures, not statewide totals. Michigan/platform fingerprints remain in `registry/dashboard_fingerprints.json` and the Maine run's `national-layers/watch-fingerprints.csv`; a fingerprint is not a verified election-night feed.

## Regeneration and interpretation

1. Retain `registry/us_primary_election_localities.csv`, `registry/local_site_discovery_leads.csv`, `audit/local-site-discovery-attempts.csv`, `registry/dashboard_fingerprints.json`, and other registries. They remain committed to main.
2. Run `python scripts/build_national_where_to_look.py` and `python -m scripts.audit_national_starting_point_coverage`. Preserve generated `audit/national-where-to-look*.csv` and summary JSON in long-term storage; the daily Actions artifact is **not** permanent storage.
3. Interpret `observed_link_candidate` as an evidence-backed URL candidate only. `verified` in the registry is **not** a verified live refresh. State fallback URLs do not demonstrate that a local authority has its own results page. URL-derived origin/host/extension classifications are hints only; do not promote them to confirmed reusable portals or data formats without direct evidence.
4. Preserve the watcher quarantine and Maine partial/structurally-unresolved outcomes without relabeling them as absent sources.

## Shutdown

The two relevant recurring workflows are **National results discovery watch** (`.github/workflows/national-results-watch.yml`) and **National where-to-look inventory** (`.github/workflows/national-where-to-look.yml`). GitHub's connected tools do not expose the disable-workflow action. After confirming a long-term copy of the generated inventory and checkpoint, disable each at the GitHub Actions workflow page using **… → Disable workflow**. This note does not claim that either workflow has been disabled.

See issue #79 and merged PR #80 for the scope and evidence contract.
