# Dashboard handoff and deployment topology inventory — v1

## Purpose
Preserve official-page → dashboard handoffs, including unfamiliar destinations, while supporting a later **wider structural sweep** across hosting, CMS templates, provisioning, vendor deployment, election archives, assets, and payload schemas. This is a schema and operating protocol, **not** a claim that all discovered URLs have been re-fetched or verified.

## Evidence layers
1. **Source pages**: `source_id,url_original,url_final,authority,jurisdiction,page_role,http_status,content_type,fetched_at,snapshot_sha256,snapshot_path`.
2. **Handoff edges**: `edge_id,source_id,destination_id,edge_type,raw_target,link_text,surrounding_text,html_locator,redirect_code,discovery_method,observed_at,evidence_ref`. Keep every official referral and the original target, even when destinations deduplicate.
3. **Dashboard destinations**: `destination_id,url_original,url_normalized,host,registrable_domain,path_segments_json,query_pairs_json,fragment,first_seen,last_seen,fetch_status`. Do not discard case, fragments, or query strings before storing raw observations.
4. **Technical observations**: append-only JSONL with `observation_id,destination_id,observed_at,headers,dom_signatures,script_urls,asset_hashes,framework_hints,api_requests,download_links,response_formats,refresh_mechanism,snapshot_ref`. Unknown means unobserved, not absent.
5. **Extraction evidence**: `extraction_id,destination_id,artifact_url,adapter,adapter_version,status,schema_fingerprint,contest_count,precinct_count,validation_result,error_class,evidence_ref`.
6. **Cluster memberships**: `destination_id,cluster_dimension,cluster_id,signature_evidence,confidence,algorithm_version,review_status`. URL, application, deployment, and payload clustering are independent; overlapping memberships are expected.
7. **Investigation queue**: `destination_id,priority,reason,next_action,status,owner,evidence_ref`.
8. **Deployment topology**: `destination_id,host_deployment_key,tenant_boundary_status,tenant_token_candidate,election_token_candidate,view_token_candidate,stable_path_prefix,variable_segments_json,configuration_assets_json,comparison_group,topology_evidence_ref,confidence`. Allowed boundary states: `unknown`, `hypothesized`, `observed`, `contradicted`; default **unknown**. A path token is not verified as a tenant merely because it resembles a county name.

## Cross-scale reinspection
Preserve a **larger-structure comparison key** for each URL: official-site template/CMS → outbound destination → deployment host → tenant candidate → election candidate → view → payload/API family. This prevents tunnel vision on vendor-specific URL patterns.

At each review checkpoint:
- Compare URL/path and asset signatures **across counties and across election years**, including previously unclassified URLs.
- Revisit source-site navigation, redirects, iframes, scripts, archival pages, and common parent domains; look for previously missed outbound handoffs.
- Look for shared application bundles, configuration manifests, API prefixes, download layouts, and response schemas even when hostnames differ.
- Examine cluster outliers and negative evidence; split or merge **derived** clusters without altering raw observations.
- Record `reviewed_at,inventory_revision,scope,unclassified_count,new_edges,new_destinations,new_clusters,merged_clusters,followup_queries` in an append-only review log.
- Keep historical and election-night evidence separate; do not mark a live source or served jurisdiction verified without direct evidence.

## Cadence and completion gates
Run the broad structural sweep after the initial handoff inventory, again after the first family-clustering pass, and at subsequent investigation checkpoints (for example after a few hours of active processing). These are **workflow checkpoints**, not a background job or scheduled automation.

Initial acceptance criteria: reproducible handoff edges with source provenance; normalized destinations with original URLs retained; explicit unknown tenant boundaries; representative URLs and supporting evidence for each derived cluster; a review log with unresolved broader structural hypotheses.

## Existing source artifacts
- `registry/discovered_result_sources.csv`: curated candidate catalog, not a complete national inventory.
- `audit/dashboard-discovery/dashboard-evidence.jsonl`: observed referral evidence, including `provenance.page_url`, `raw_target`, `kind`, and `label`.
- `registry/dashboard_fingerprints.json`: existing family rules, not exhaustive classifications.

Example observed Enhanced Voting URL: `https://app.enhancedvoting.com/results/public/berrien-county-mi/elections/2026Augustelection`. Treat `berrien-county-mi` and `2026Augustelection` as **candidate** tenant and election tokens pending comparison or payload verification.
