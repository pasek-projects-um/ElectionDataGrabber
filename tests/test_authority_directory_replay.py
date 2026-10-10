import csv
import hashlib

import pytest

from scripts import replay_national_authority_directories as command


def write_rows(path, fields, rows):
    with path.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


@pytest.fixture
def evidence(tmp_path, monkeypatch):
    registry = tmp_path / "registry"
    registry.mkdir()
    snapshots = tmp_path / "snapshots"
    snapshots.mkdir()
    units = [{"state": "XY", "canonical_name": name, "jurisdiction_id": str(i)}
             for i, name in enumerate(("Alpha", "Beta", "Gamma", "Delta"))]
    write_rows(registry / "us_primary_election_localities.csv", units[0].keys(), units)
    write_rows(registry / "us_primary_election_locality_denominators.csv",
               ["state", "expected_primary_units", "estimate_status"],
               [{"state": "XY", "expected_primary_units": 4, "estimate_status": "provisional"}])
    url = "https://state.gov/directory"
    write_rows(registry / "us_state_central_authority_sources.csv",
               ["state", "central_authority_url"], [{"state": "XY", "central_authority_url": url}])
    write_rows(registry / "discovered_result_sources.csv",
               ["url", "observed_from", "catalog_kind", "target_status"],
               [{"url": "https://alpha.gov/results", "observed_from": "https://alpha.gov/clerk",
                 "catalog_kind": "results_page_lead", "target_status": "fetched"},
                {"url": "https://beta.gov/results", "observed_from": "https://beta.gov/clerk",
                 "catalog_kind": "results_page_lead", "target_status": "fetch_unresolved"}])
    html = ('<a href="https://alpha.gov/clerk">Alpha Clerk</a>'
            '<a href="https://beta.gov/clerk">Beta Clerk</a>'
            '<li>Gamma and Delta <a href="https://shared.gov/clerk">Website</a></li>')
    digest = hashlib.sha256(html.encode()).hexdigest()
    (snapshots / (digest + ".html")).write_text(html)
    captured = {"pages": {url: {"snapshot_sha256": digest, "status": "fetched",
                                "last_success_at": 100}}}
    monkeypatch.setattr(command, "build", lambda root: ([
        {"jurisdiction_id": "2", "page_role": "state_directory_fallback", "url": url}], [], {}))
    return registry, captured, snapshots


def test_observed_unfetched_and_ambiguous_evidence_keep_separate_buckets(evidence):
    candidates, states, units, summary = command.replay(*evidence)
    assert [r["bucket"] for r in units] == ["observed_result_page_candidate",
        "evidence_backed_hunting_location", "unresolved_location", "unresolved_location"]
    assert any(r["match_status"] == "ambiguous_unit_label" for r in candidates)
    assert states[0]["units_with_unique_directory_hunting_clue"] == 2
    assert summary["network_requests_in_replay"] == 0
    assert all(r["served_jurisdiction_verified"] == r["live_coverage"] == "false" for r in units)


def test_missing_capture_does_not_turn_state_fallback_into_local_evidence(evidence):
    registry, captured, snapshots = evidence
    for path in snapshots.iterdir():
        path.unlink()
    _, states, units, _ = command.replay(registry, captured, snapshots)
    assert not states[0]["capture_available"]
    assert all(r["bucket"] == "unresolved_location" for r in units)


def test_changed_capture_is_rejected(evidence):
    registry, captured, snapshots = evidence
    next(snapshots.iterdir()).write_text("modified capture")
    with pytest.raises(ValueError, match="digest mismatch"):
        command.replay(registry, captured, snapshots)


def test_http_success_challenge_is_not_a_usable_directory(evidence):
    registry, captured, snapshots = evidence
    html = '<html><script src="/_Incapsula_Resource?challenge=example"></script><body></body></html>'
    digest = hashlib.sha256(html.encode()).hexdigest()
    (snapshots / (digest + ".html")).write_text(html)
    next(iter(captured["pages"].values()))["snapshot_sha256"] = digest
    candidates, states, units, summary = command.replay(registry, captured, snapshots)
    assert not candidates
    assert states[0]["fetch_status"] == "fetched"
    assert states[0]["capture_access_state"] == "blocked_html"
    assert summary["captured_state_pages"] == 1 and summary["usable_state_captures"] == 0
    assert all(r["bucket"] == "unresolved_location" for r in units)
