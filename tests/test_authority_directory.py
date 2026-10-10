from election_data_grabber.authority_directory import extract_directory

PAGE = "https://state.gov/election-offices"
UNITS = [{"state": "XY", "canonical_name": name, "jurisdiction_id": f"unit:{index}"}
         for index, name in enumerate(("Alpha", "Beta", "York", "New York"))]


def test_observed_links_keep_unit_and_parent_evidence_without_promotion():
    rows, gaps = extract_directory(PAGE, '<a href="https://alpha.gov/clerk">Alpha County</a>',
                                   UNITS, state="XY")
    assert rows[0]["associated_unit_ids"] == "unit:0"
    assert rows[0]["observed_from"] == PAGE
    assert rows[0]["served_jurisdiction_verified"] == "false"
    assert len(rows[0]["snapshot_sha256"]) == 64
    assert len(gaps) == 3


def test_website_label_can_use_a_single_directory_row_with_base_url():
    rows, _ = extract_directory(PAGE, '<base href="https://directory.gov/local/">'
        '<table><tr><td>Beta County Clerk</td><td><a href="beta">Website</a></td></tr></table>',
        UNITS, state="XY")
    assert rows[0]["url"] == "https://directory.gov/local/beta"
    assert rows[0]["associated_unit_ids"] == "unit:1"
    assert rows[0]["match_basis"] == "directory_row"


def test_overlapping_names_and_multiple_entries_remain_distinct():
    rows, gaps = extract_directory(PAGE, '<a href="/newyork">New York County</a>'
        '<li>Alpha and Beta <a href="/shared">Election office</a></li>', UNITS, state="XY")
    single = next(r for r in rows if r["url"].endswith("/newyork"))
    assert single["associated_unit_ids"] == "unit:3"
    shared = next(r for r in rows if r["url"].endswith("/shared"))
    assert shared["match_status"] == "ambiguous_unit_label"
    assert len(gaps) == 4  # A label alone on an arbitrary internal path is not a website lead.


def test_duplicate_names_cannot_establish_unique_authority():
    units = UNITS + [{"state": "XY", "canonical_name": "Alpha", "jurisdiction_id": "other"}]
    rows, gaps = extract_directory(PAGE, '<a href="/alpha">Alpha</a>', units, state="XY")
    assert rows[0]["match_status"] == "ambiguous_unit_label"
    assert len(gaps) == 5


def test_social_contacts_transient_urls_and_artifacts_do_not_clear_units():
    rows, gaps = extract_directory(PAGE, '<a href="https://facebook.com/alpha">Alpha</a>'
        '<a href="mailto:clerk@example.test">Alpha</a>'
        '<a href="/alpha?token=secret">Alpha</a><a href="/alpha.pdf">Alpha County</a>',
        UNITS, state="XY")
    assert len(rows) == 1 and rows[0]["match_status"] == "artifact_lead"
    assert len(gaps) == 4


def test_block_or_shell_is_access_followup_not_no_authority():
    for html in ('<title>Radware Captcha Page</title>', '<app-root></app-root>'):
        rows, gaps = extract_directory(PAGE, html, UNITS, state="XY")
        assert not rows and len(gaps) == 4
        assert all(g["next_action"] == "resolve_directory_access" for g in gaps)


def test_unmatched_authority_links_are_retained_for_review_and_names_are_state_scoped():
    units = UNITS + [{"state": "ZZ", "canonical_name": "Gamma", "jurisdiction_id": "zz"}]
    rows, gaps = extract_directory(PAGE, '<a href="/gamma-clerk">Gamma Clerk</a>',
                                   units, state="XY")
    assert rows[0]["match_status"] == "unmatched_directory_link"
    assert not rows[0]["associated_unit_ids"] and len(gaps) == 4


def test_in_page_anchors_do_not_resolve_local_authority_website():
    rows, gaps = extract_directory(PAGE, '<a href="#alpha">Alpha County</a>', UNITS, state="XY")
    assert rows[0]["match_status"] == "directory_anchor" and len(gaps) == 4


def test_maps_documents_and_other_unit_links_do_not_become_authority_websites():
    rows, gaps = extract_directory(PAGE,
        '<a href="/maps/sd/alpha.html">Alpha County</a>'
        '<a href="/media/92">Beta County Wait Time Reduction Plan</a>'
        '<a href="/candidates/york.html">York County</a>', UNITS, state="XY")
    assert {r["link_role"] for r in rows} == {"document_or_map_lead", "other_unit_link"}
    assert len(gaps) == 4


def test_historical_results_are_a_distinct_hunting_clue():
    rows, gaps = extract_directory(PAGE,
        '<tr><td>Alpha County 2016 Election</td><td>'
        '<a href="/elections/resultsarchive/2016/alpha.html">Results</a></td></tr>',
        UNITS, state="XY")
    assert rows[0]["link_role"] == "result_page_lead"
    assert rows[0]["served_jurisdiction_verified"] == "false" and len(gaps) == 3


def test_details_summary_matches_official_county_display_form_without_changing_ids():
    units = [{"state": "MD", "canonical_name": "Allegany County",
              "jurisdiction_id": "us:md:census-county:24001", "jurisdiction_level": "county_equivalent"}]
    html = '<details><summary>Allegany</summary><dl><dt>Website</dt><dd>'
    html += '<a href="http://alleganygov.org/158/Election-Office">'
    html += 'http://alleganygov.org/158/election-office</a></dd></dl></details>'
    rows, gaps = extract_directory("https://elections.maryland.gov/about/county_boards.html",
                                   html, units, state="MD")
    assert rows[0]["associated_unit_ids"] == "us:md:census-county:24001"
    assert rows[0]["match_basis"] == "details_summary" and not gaps


def test_administrative_suffix_alias_preserves_ambiguity():
    units = [{"state": "XY", "canonical_name": name, "jurisdiction_level": "county_equivalent",
              "jurisdiction_id": str(i)} for i, name in enumerate(("Alpha County", "Alpha Parish"))]
    rows, gaps = extract_directory(PAGE,
        '<details><summary>Alpha</summary><a href="https://alpha.gov/clerk">Website</a></details>',
        units, state="XY")
    assert rows[0]["match_status"] == "ambiguous_unit_label" and len(gaps) == 2


def test_directory_watcher_emits_and_retains_review_queue_without_auto_follow(tmp_path):
    from election_data_grabber.discovery_watch import follow_candidates, run_watch

    seeds = [{"url": PAGE, "states": "XY", "page_roles": "state_directory_fallback"}]
    html = '<li>Alpha County Clerk <a href="https://alpha.gov/clerk">Website</a></li>'
    state, events, summary = run_watch(
        seeds, tmp_path / "state.json", tmp_path / "snapshots", lambda url: (url, html),
        now=100, interval=60, localities=UNITS)
    assert summary["retained_authority_link_candidates"] == 1
    assert any(e["kind"] == "authority_link_candidate" for e in events)
    assert len(state["pages"][PAGE]["directory_extraction"]["XY"]["unresolved_unit_ids"]) == 3
    assert not any(s["url"] == "https://alpha.gov/clerk" for s in follow_candidates(seeds, state, 2))
    state, events, _ = run_watch(
        seeds, tmp_path / "state.json", tmp_path / "snapshots",
        lambda url: (url, '<title>Access Denied</title>'), now=160, interval=60, localities=UNITS)
    assert len(state["authority_candidates"]) == 1
    assert not any(e["kind"] == "authority_link_candidate" for e in events)


def test_scheduled_command_exports_authority_queue_from_named_registry(tmp_path, monkeypatch):
    import csv
    import sys

    import scripts.watch_national_results as command

    registry = tmp_path / "registry"
    registry.mkdir()
    (registry / "us_primary_election_localities.csv").write_text(
        "state,canonical_name,jurisdiction_id\nXY,Alpha,unit:0\n")
    seeds = tmp_path / "seeds.csv"
    seeds.write_text("url,states,page_roles\n" + PAGE + ",XY,state_directory_fallback\n")

    class CaptureFetcher:
        def __init__(self, *args, **kwargs):
            self.requests = 0

        def __call__(self, url):
            self.requests += 1
            return url, '<a href="https://alpha.gov/clerk">Alpha County Clerk</a>'

        def close(self):
            pass

    monkeypatch.setattr(command, "WatchFetcher", CaptureFetcher)
    monkeypatch.setattr(sys, "argv", ["watch", "--registry", str(registry),
        "--seeds", str(seeds), "--source-seeds", str(tmp_path / "unused.csv"),
        "--state-dir", str(tmp_path / "worker")])
    command.main()
    with (tmp_path / "worker/authority-link-queue.csv").open() as stream:
        rows = list(csv.DictReader(stream))
    assert len(rows) == 1
    assert rows[0]["associated_unit_ids"] == "unit:0"
    assert rows[0]["served_jurisdiction_verified"] == "false"
