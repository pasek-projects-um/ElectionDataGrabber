import json
from datetime import UTC, datetime

import httpx
import pytest
from pydantic import ValidationError
from typer.testing import CliRunner

from election_data_grabber.cli import app
from election_data_grabber.election_night import (
    Feed,
    FeedFetcher,
    Manifest,
    collect,
    collector_lock,
    connect,
    parse_capture,
    replay_sample,
    report,
)

CSV = b"precinct,office,candidate,total\nP1,Mayor,Alice,12\n"
NOW = 1793750400


def manifest(**changes):
    fields = {
        "source_id": "test-feed",
        "state": "MI",
        "jurisdiction_id": "us:mi:county:test",
        "authority_id": "us:authority:mi:county-clerk:test",
        "election_id": "2026-general",
        "url": "https://county.gov/results.csv",
        "parser": "csv",
        "enabled": True,
        "authority_evidence_url": "https://county.gov/elections",
        "election_evidence_url": "https://county.gov/2026-general",
        "reviewed_at": "2026-10-21T17:00:00Z",
        "update_semantics": "cumulative",
    }
    fields.update(changes)
    return Manifest(election_id="2026-general", election_date="2026-11-03", feeds=[Feed(**fields)])


class Fetch:
    def __init__(self, body=CSV, status=200, error=None):
        self.body, self.status, self.error = body, status, error
        self.calls = []

    def fetch_feed(self, url, validators):
        self.calls.append((url, validators))
        if self.error:
            raise self.error
        return self.status, self.body, url, {"etag": "v1"}


def test_capture_restart_replay_and_conditional_request(tmp_path):
    first = collect(manifest(), tmp_path, fetch=Fetch(), now=NOW)
    result = first["results"][0]
    assert first["replay_tested_feeds"] == 1
    assert result["status"] == "ok"
    assert replay_sample(tmp_path, result["sample_path"])["replay_match"]
    sample = json.loads((tmp_path / result["sample_path"]).read_bytes())
    obs = sample["observations"][0]
    assert obs["snapshot_sha256"] == result["snapshot_sha256"]
    assert obs["reporting_regime_id"] and obs["election_id"] == "2026-general"
    assert not collect(manifest(), tmp_path, fetch=Fetch(), now=NOW + 1)["results"]
    fetch = Fetch(status=304, body=b"")
    again = collect(manifest(), tmp_path, fetch=fetch, now=NOW + 60)
    assert fetch.calls[0][1] == {"If-None-Match": "v1"}
    assert again["results"][0]["changed_rows"] == 0
    assert again["refresh_verified_feeds"] == 0
    assert len(list((tmp_path / "raw").iterdir())) == 1
    assert len(list((tmp_path / "samples").iterdir())) == 1
    assert len(list((tmp_path / "captures").iterdir())) == 2


def test_changed_results_and_identity_are_stable_across_restart(tmp_path):
    one = collect(manifest(), tmp_path, fetch=Fetch(), now=NOW)
    two = collect(manifest(), tmp_path, fetch=Fetch(CSV.replace(b"12", b"15")), now=NOW + 60)
    assert two["results"][0]["changed_rows"] == 1
    assert two["results"][0]["update_observed"]
    ids = []
    for summary in (one, two):
        sample = json.loads((tmp_path / summary["results"][0]["sample_path"]).read_bytes())
        ids.append(sample["observations"][0]["reporting_unit_id"])
    assert ids[0] == ids[1]


@pytest.mark.parametrize(
    "body,warning",
    [
        (CSV.replace(b"12", b"11"), "cumulative_votes_decreased"),
        (CSV.replace(b"P1", b"P2"), "rows_disappeared"),
    ],
)
def test_reviews_preserve_accepted_baseline(tmp_path, body, warning):
    one = collect(manifest(), tmp_path, fetch=Fetch(), now=NOW)
    two = collect(manifest(), tmp_path, fetch=Fetch(body), now=NOW + 60)
    assert two["results"][0]["status"] == "review_required"
    assert warning in two["feeds"][0]["warnings"]
    assert two["feeds"][0]["sample_path"] == one["feeds"][0]["sample_path"]
    assert two["feeds"][0]["last_success_at"] == NOW
    # A second suspicious capture must not silently become the accepted baseline.
    three = collect(manifest(), tmp_path, fetch=Fetch(body), now=NOW + 120)
    assert three["results"][0]["status"] == "review_required"


@pytest.mark.parametrize(
    "body",
    [
        b"<html>challenge</html>",
        b"precinct,office,candidate,total\n",
        CSV + b"P1,Mayor,Alice,12\n",
        CSV.replace(b"12", b"-1"),
    ],
)
def test_invalid_payload_is_preserved_without_losing_baseline(tmp_path, body):
    one = collect(manifest(), tmp_path, fetch=Fetch(), now=NOW)
    two = collect(manifest(), tmp_path, fetch=Fetch(body), now=NOW + 60)
    assert two["results"][0]["status"] == "failed"
    assert (tmp_path / two["results"][0]["body_path"]).read_bytes() == body
    assert two["feeds"][0]["sample_path"] == one["feeds"][0]["sample_path"]
    assert two["feeds"][0]["failures"] == 1


def test_network_failure_backoff_and_stale_status(tmp_path):
    collect(manifest(), tmp_path, fetch=Fetch(), now=NOW)
    failed = collect(
        manifest(), tmp_path, fetch=Fetch(error=httpx.ReadTimeout("timeout")), now=NOW + 60
    )
    assert failed["results"][0]["status"] == "failed"
    assert report(manifest(), tmp_path, now=NOW + 301)["stale_enabled_feeds"] == 1


def test_config_change_invalidates_baseline_and_conditionals(tmp_path):
    collect(manifest(), tmp_path, fetch=Fetch(), now=NOW)
    fetch = Fetch()
    fresh = collect(
        manifest(election_evidence_url="https://county.gov/reviewed"),
        tmp_path,
        fetch=fetch,
        now=NOW + 1,
    )
    assert fetch.calls[0][1] == {}
    assert fresh["results"][0]["common_rows"] == 0


def test_disabled_candidates_never_fetched(tmp_path):
    fetch = Fetch()
    summary = collect(manifest(enabled=False), tmp_path, fetch=fetch, now=NOW)
    assert summary["enabled_feeds"] == 0
    assert not fetch.calls


def test_manifest_rejects_unreviewed_wrong_state_and_mixed_elections():
    for kwargs in [
        {"authority_evidence_url": ""},
        {"reviewed_at": None},
        {"state": "OH"},
        {"url": "file:///tmp/results"},
        {"election_id": "wrong-election"},
    ]:
        with pytest.raises((ValueError, ValidationError)):
            manifest(**kwargs)
    m = manifest()
    with pytest.raises(ValidationError, match="Duplicate source_id"):
        Manifest(election_id=m.election_id, election_date=m.election_date, feeds=m.feeds * 2)


def test_missing_304_baseline_and_tampered_raw_fail(tmp_path):
    missing = collect(manifest(), tmp_path, fetch=Fetch(status=304, body=b""), now=NOW)
    assert missing["results"][0]["status"] == "failed"
    success = collect(manifest(), tmp_path, fetch=Fetch(), now=NOW + 60)
    result = success["results"][0]
    (tmp_path / result["body_path"]).write_bytes(b"tampered")
    with pytest.raises(ValueError, match="digest mismatch"):
        replay_sample(tmp_path, result["sample_path"])
    health = report(manifest(), tmp_path, now=NOW + 61)
    assert health["feeds"][0]["status"] == "artifact_integrity_failed"
    assert health["replay_tested_feeds"] == 0


def test_small_batch_and_cancel_resume_other_feeds(tmp_path):
    m = manifest()
    other = m.feeds[0].model_copy(update={"source_id": "z-other"})
    m.feeds.append(other)
    first = collect(m, tmp_path, fetch=Fetch(), now=NOW, max_feeds=1)
    assert first["stop_reason"] == "feed_limit"
    second = collect(m, tmp_path, fetch=Fetch(), now=NOW + 1, max_feeds=1)
    assert second["results"][0]["source_id"] == "z-other"
    from election_data_grabber.discovery_watch import TimeBudgetExhausted

    third = collect(m, tmp_path, fetch=Fetch(error=TimeBudgetExhausted()), now=NOW + 60)
    assert third["stop_reason"] == "time_request_budget_or_signal"
    assert third["feeds"][0]["last_success_at"] == NOW


def test_collector_lock_and_sqlite_atomic_attempts(tmp_path):
    with (
        collector_lock(tmp_path / "collector.lock"),
        pytest.raises(RuntimeError, match="Another collector"),
    ):
        collect(manifest(), tmp_path, fetch=Fetch(), now=NOW)
    collect(manifest(), tmp_path, fetch=Fetch(), now=NOW)
    db = connect(tmp_path)
    try:
        assert db.execute("SELECT COUNT(*) FROM attempts").fetchone()[0] == 1
        assert db.execute("SELECT last_success FROM feeds").fetchone()[0] == NOW
    finally:
        db.close()


def test_cli_status_fails_closed_for_empty_manifest(tmp_path):
    path = tmp_path / "manifest.json"
    path.write_text(
        Manifest(election_id="2026-general", election_date="2026-11-03", feeds=[]).model_dump_json()
    )
    result = CliRunner().invoke(app, ["status", str(path), "--state-dir", str(tmp_path / "state")])
    assert result.exit_code == 1
    assert json.loads(result.stdout)["enabled_feeds"] == 0


def test_fetcher_robots_redirects_conditional_and_byte_budget():
    requested = []

    def transport(request):
        requested.append(request)
        if request.url.path == "/robots.txt":
            return httpx.Response(404)
        if request.url.host == "county.gov":
            return httpx.Response(302, headers={"location": "https://other.gov/feed.csv"})
        return httpx.Response(200, content=CSV)

    fetch = FeedFetcher(delay=0, max_requests=10, max_bytes=10)
    fetch.client.close()
    fetch.client = httpx.Client(transport=httpx.MockTransport(transport))
    try:
        with pytest.raises(ValueError, match="byte budget"):
            fetch.fetch_feed("https://county.gov/results.csv", {"If-None-Match": "secret-etag"})
        assert len(requested) == 4
        assert "If-None-Match" not in requested[-1].headers
    finally:
        fetch.close()


def test_washtenaw_election_identity_is_explicit():
    body = b"""<h2>Test County</h2><table><tr><td>Governor</td></tr>
      <tr><td>Alice</td><td>1</td><td>2</td><td>3</td><td>6</td></tr></table>"""
    rows = parse_capture(
        manifest(parser="washtenaw").feeds[0], body, datetime.fromtimestamp(NOW, UTC)
    )
    assert len(rows) == 4
    assert {row["election_id"] for row in rows} == {"2026-general"}


def test_washtenaw_production_headers_keep_district_numbers():
    body = b"""<table><tr><td class='headertr' colspan='4'>State Senator 14 DEM</td>
    <td class='headertr' colspan='2'><a href='detail.html'>View Precinct Detail</a></td></tr>
    <tr><td>Alice</td><td>1</td><td>2</td><td>3</td><td>6</td><td>100%</td></tr></table>"""
    rows = parse_capture(
        manifest(
            parser="washtenaw", reporting_unit_name="Test County", reporting_unit_type="county"
        ).feeds[0],
        body,
        datetime.fromtimestamp(NOW, UTC),
    )
    assert len(rows) == 4
    assert {row["contest_name"] for row in rows} == {"State Senator 14 DEM"}
    assert {row["reporting_unit_name"] for row in rows} == {"Test County"}


def test_readiness_keeps_candidates_and_current_feeds_separate(tmp_path):
    from pathlib import Path

    from election_data_grabber.election_readiness import readiness

    config = Manifest(election_id="2026-general", election_date="2026-11-03", feeds=[])
    evidence = readiness(Path("registry"), config, tmp_path)
    national = evidence["national"]
    assert national["state_count"] == 51
    assert (
        national["units_with_any_direct_candidate"] >= national["units_with_core_direct_evidence"]
    )
    assert (
        national["historically_verified_election_night_capability_units"] < national["named_units"]
    )
    assert evidence["collector"]["enabled_feeds"] == 0
    assert evidence["national_ready"] is False
    assert evidence["population_weighted_coverage"] is None
    assert evidence["reporting_place_weighted_coverage"] is None


def test_live_poll_rehearsal_across_multiple_parsers(tmp_path):
    cases = [
        (
            "json",
            (
                b'{"reporting_units":[{"id":"P1","name":"P1","contests":[{"name":"Mayor",'
                b'"choices":[{"name":"Alice","votes":12}]}]}]}'
            ),
        ),
        (
            "clarity_xml",
            (
                b'<Results><Precinct id="p1" name="P1"><Contest name="Mayor">'
                b'<Choice name="Alice"><Total mode="total" votes="12"/></Choice></Contest>'
                b"</Precinct></Results>"
            ),
        ),
        (
            "enhanced_voting",
            (
                b'<script id="__NEXT_DATA__" type="application/json">'
                b'{"props":{"pageProps":{"results":[{"precinctName":"P1","contestName":"Mayor",'
                b'"candidateName":"Alice","total":12}]}}}</script>'
            ),
        ),
    ]
    for parser, body in cases:
        state = tmp_path / parser
        summary = collect(manifest(parser=parser), state, fetch=Fetch(body), now=NOW)
        assert summary["results"][0]["status"] == "ok"
        assert replay_sample(state, summary["results"][0]["sample_path"])["replay_match"]


@pytest.mark.parametrize("votes", [None, True, 12.5, ""])
def test_json_does_not_impute_missing_or_truncate_fractional_votes(votes):
    body = json.dumps(
        {
            "reporting_units": [
                {
                    "id": "p1",
                    "name": "P1",
                    "contests": [{"name": "Mayor", "choices": [{"name": "Alice", "votes": votes}]}],
                }
            ]
        }
    ).encode()
    with pytest.raises(ValueError, match="explicit integer"):
        parse_capture(manifest(parser="json").feeds[0], body, datetime.fromtimestamp(NOW, UTC))


def test_partial_csv_failure_cannot_silently_omit_a_choice(tmp_path):
    summary = collect(
        manifest(), tmp_path, fetch=Fetch(CSV + b"P1,Mayor,Bob,not-reported\n"), now=NOW
    )
    assert summary["results"][0]["status"] == "failed"
    assert summary["replay_tested_feeds"] == 0


def test_refresh_requires_operator_evidence_and_two_changed_accepted_samples(tmp_path):
    from election_data_grabber.election_refresh import verify_refresh

    config = manifest()
    one = collect(config, tmp_path, fetch=Fetch(), now=NOW)["results"][0]["sample_path"]
    two = collect(config, tmp_path, fetch=Fetch(CSV.replace(b"12", b"15")), now=NOW + 60)[
        "results"
    ][0]["sample_path"]
    assert report(config, tmp_path, now=NOW + 60)["refresh_verified_feeds"] == 0
    proof = verify_refresh(
        config,
        tmp_path,
        one,
        two,
        evidence_url="https://county.gov/2026-general",
        note="Reviewed update",
    )
    assert proof["refresh_verified"]
    assert report(config, tmp_path, now=NOW + 60)["refresh_verified_feeds"] == 1
    assert (
        report(manifest(reviewed_at="2026-10-22T00:00:00Z"), tmp_path, now=NOW + 60)[
            "refresh_verified_feeds"
        ]
        == 0
    )
    with pytest.raises(ValueError, match="increasing"):
        verify_refresh(
            config,
            tmp_path,
            two,
            one,
            evidence_url="https://county.gov/2026-general",
            note="Reviewed",
        )


def test_historical_captures_cannot_verify_november_refresh(tmp_path):
    from election_data_grabber.election_refresh import verify_refresh

    one = collect(manifest(), tmp_path, fetch=Fetch(), now=NOW - 86400 * 30)
    two = collect(
        manifest(), tmp_path, fetch=Fetch(CSV.replace(b"12", b"15")), now=NOW - 86400 * 30 + 60
    )
    with pytest.raises(ValueError, match="reporting window"):
        verify_refresh(
            manifest(),
            tmp_path,
            one["results"][0]["sample_path"],
            two["results"][0]["sample_path"],
            evidence_url="https://county.gov/elections",
            note="Historical test",
        )
