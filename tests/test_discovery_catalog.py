from election_data_grabber.discovery_catalog import catalog_sources, write_catalog
from election_data_grabber.national_discovery import discover, publisher_key


def checkpoint(html, status="fetched"):
    url = "https://county.gov/election-results"
    rows = discover(url, html)
    pubs = {}
    for row in rows:
        key = publisher_key(row["url"])
        pubs.setdefault(key, {"candidates": {}})["candidates"][row["url"]] = row
    return {
        "publishers": pubs,
        "pages": {url: {"status": status, "sha256": "digest", "final_url": url}},
        "associations": [{"candidate_url": r["url"], "seed_url": url} for r in rows],
    }


def test_catalog_separates_artifacts_cms_and_dashboards(tmp_path):
    state = checkpoint(
        '<p>CivicPlus</p><a href="/2024/results.pdf">2024 Election results</a>'
        '<a href="https://app.enhancedvoting.com/results/public/a/elections/x">View</a>'
    )
    seeds = [
        {
            "url": "https://county.gov/election-results",
            "state": "MI",
            "page_role": "local_election_authority",
            "evidence_registry": "fixture",
        }
    ]
    rows = catalog_sources([(state, seeds)], observed_date="2026-10-09")
    assert {r["catalog_kind"] for r in rows} == {
        "authority_cms",
        "dashboard_candidate",
        "result_artifact_lead",
    }
    assert all(r["states"] == "MI" and r["live_coverage"] == "false" for r in rows)
    artifact = next(r for r in rows if r["catalog_kind"] == "result_artifact_lead")
    assert artifact["observed_years"] == "2024" and artifact["verification_status"] == "candidate"
    summary = write_catalog(rows, tmp_path / "catalog.csv")
    assert summary["cataloged_urls"] == 3 and summary["verified_live_sources"] == 0


def test_catalog_excludes_unrelated_artifact_and_vendor_assets():
    url = "https://county.gov/"
    rows = discover(
        url,
        '<a href="/budget.pdf">Budget</a><script src="https://results.enr.clarityelections.com/app.js"></script>',
    )
    state = {"publishers": {r["url"]: {"candidates": {r["url"]: r}} for r in rows}, "pages": {}}
    assert catalog_sources([(state, [])], observed_date="2026-10-09") == []


def test_catalog_keeps_successful_fetch_and_provenance_across_batches():
    seed = {
        "url": "https://county.gov/election-results",
        "state": "MI",
        "page_role": "statewide_results_lead",
    }
    yes = checkpoint("<p>Election results 2024</p>")
    no = checkpoint("<p>Election results 2024</p>", "fetch_failed")
    rows = catalog_sources([(yes, [seed]), (no, [seed])], observed_date="2026-10-09")
    assert len(rows) == 1 and rows[0]["verification_status"] == "fetched_unverified"
    assert rows[0]["source_scopes"] == "statewide_results_lead"
    assert rows[0]["served_jurisdiction_verified"] == "false"


def test_offline_replay_preserves_crlf_and_rejects_tampering(tmp_path):
    import hashlib

    import pytest

    from scripts.replay_discovery_snapshots import replay

    html = "<title>Election Results</title>\r\n<p>Election results 2026</p>\r\n"
    digest = hashlib.sha256(html.encode()).hexdigest()
    snapshots = tmp_path / "snapshots"
    snapshots.mkdir()
    (snapshots / (digest + ".html")).write_bytes(html.encode())
    url = "https://county.gov/election-results"
    captured = {
        "pages": {
            url: {
                "status": "fetched",
                "sha256": digest,
                "final_url": url,
                "candidates": [],
                "text": "Election results 2026",
            }
        }
    }
    seeds = [{"url": url, "jurisdiction_id": "county"}]
    state = replay(captured, seeds, snapshots, tmp_path / "replay.json")
    assert state["summary"]["http_requests_this_run"] == 0
    assert url in state["publishers"]
    (snapshots / (digest + ".html")).write_text("tampered")
    with pytest.raises(ValueError, match="digest"):
        replay(captured, seeds, snapshots, tmp_path / "tampered.json")


def test_published_catalog_preserves_unique_evidence_and_zero_coverage():
    import csv
    from pathlib import Path

    from election_data_grabber.national_discovery import normalize

    with Path("registry/discovered_result_sources.csv").open() as stream:
        rows = list(csv.DictReader(stream))
    assert len(rows) == len({r["url"] for r in rows})
    assert all(normalize(r["url"]) == r["url"] and r["observed_from"] for r in rows)
    assert all(
        r["live_coverage"] == "false" and r["served_jurisdiction_verified"] == "false" for r in rows
    )
    assert all(not r["url"].split("?")[0].endswith((".js", ".css")) for r in rows)


def test_public_export_omits_sessions_and_redacts_contact_labels():
    from election_data_grabber.discovery_publication import (
        clean_public_candidate,
        clean_public_label,
        publishable_url,
    )

    assert publishable_url("https://county.gov/election-results?year=2026&county=alpha")
    assert not publishable_url("https://county.gov/election-results?session=temporary")
    assert not publishable_url("https://county.gov/election-results?email=person%40example.test")
    assert not publishable_url("https://county.gov/cdn-cgi/challenge-platform/verify")
    assert (
        clean_public_label("Election results contact person@example.test")
        == "Election results contact [email omitted]"
    )
    candidate = {
        "url": "https://county.gov/election-results",
        "provenance": [
            {
                "page_url": "https://county.gov/",
                "raw_target": "/election-results",
                "label": "Contact person@example.test",
            }
        ],
    }
    assert "person@" not in clean_public_candidate(candidate)["provenance"][0]["label"]
    candidate["provenance"][0]["page_url"] = "https://county.gov/?token=temporary"
    assert clean_public_candidate(candidate) is None


def test_unclassified_query_values_stay_out_of_public_catalog():
    from election_data_grabber.discovery_publication import publishable_url

    for key in ("refresh", "hash", "revision", "rev", "unknown"):
        assert not publishable_url("https://county.gov/election-results?" + key + "=opaque")
    assert publishable_url("https://county.gov/results?electionId=2026-primary&year=2026")
