from scripts.build_directory_watch_seeds import build


def row(**kwargs):
    return dict({"url": "https://county.gov/elections", "state": "MI",
                 "associated_unit_ids": "us:mi:alpha", "match_status": "unit_label_candidate",
                 "link_role": "authority_website_lead", "observed_from": "https://state.gov/",
                 "snapshot_sha256": "a" * 64, "match_basis": "anchor_label"}, **kwargs)


def test_inspection_preserves_evidence_and_alternative_associations():
    first = row()
    seeds = build([first, first, row(associated_unit_ids="us:mi:beta")])
    assert len(seeds) == 2
    assert seeds[0]["snapshot_sha256"] == "a" * 64
    assert seeds[0]["observed_from"] == "https://state.gov/"
    assert {s["associated_unit_ids"] for s in seeds} == {"us:mi:alpha", "us:mi:beta"}
    assert all(s["live_coverage"] == s["served_jurisdiction_verified"] == "false" for s in seeds)


def test_ambiguous_unproven_artifact_and_transient_links_never_become_html_seeds():
    assert build([row(match_status="ambiguous_unit_label"),
                  row(associated_unit_ids="us:mi:alpha | us:mi:beta"),
                  row(snapshot_sha256=""), row(observed_from=""),
                  row(link_role="document_or_map_lead"), row(url="https://county.gov/a.csv"),
                  row(url="https://county.gov/?token=secret"),
                  row(url="http://localhost/")]) == []
