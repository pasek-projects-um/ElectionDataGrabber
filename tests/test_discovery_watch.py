import json

import httpx
import pytest

from election_data_grabber.discovery_watch import WatchFetcher, follow_candidates, run_watch
from election_data_grabber.national_discovery import RequestBudgetExhausted
from scripts.watch_national_results import worker_lock

URL = "https://county.gov/elections"
TARGET = "https://results.enr.clarityelections.com/MI/County/123/"
SEEDS = [{"url": URL, "states": "MI", "associated_unit_ids": "county:alpha"}]


def watch(tmp_path, html, now, **kwargs):
    return run_watch(SEEDS, tmp_path / "state.json", tmp_path / "snapshots",
                     lambda url: (url, html), now=now, interval=60, **kwargs)


def test_repeated_scheduling_change_detection_and_restart(tmp_path):
    first, events, summary = watch(tmp_path, "<p>Election information</p>", 100)
    assert summary["checked_pages"] == 1
    assert [e["kind"] for e in events] == ["baseline_captured"]
    assert first["pages"][URL]["next_check_at"] == 160
    _, events, summary = watch(tmp_path, "unexpected content", 120)
    assert not events and summary["checked_pages"] == 0
    html = f'<a href="{TARGET}">2026 Election Results</a>'
    state, events, _ = watch(tmp_path, html, 160)
    assert {e["kind"] for e in events} == {"page_changed", "candidate_discovered"}
    assert state["candidates"][TARGET]["seed_associations"][0]["associated_unit_ids"] == "county:alpha"
    _, events, _ = watch(tmp_path, html, 220)
    assert events == []
    assert len(list((tmp_path / "snapshots").glob("*.html"))) == 2
    assert len(list((tmp_path / "events").glob("*.json"))) == 2
    assert all(not e["live_coverage"] for e in state["events"])


def test_link_removal_retains_candidate_and_reappearance_is_not_new(tmp_path):
    html = f'<a href="{TARGET}">Election results</a>'
    watch(tmp_path, html, 100)
    state, events, _ = watch(tmp_path, "<p>Election information</p>", 160)
    assert TARGET in state["candidates"]
    assert any(e["kind"] == "link_not_observed_this_capture" for e in events)
    _, events, summary = watch(tmp_path, html, 220)
    assert any(e["kind"] == "candidate_reappeared" for e in events)
    assert summary["new_candidates"] == 0


def test_blocks_and_errors_preserve_last_success_and_back_off(tmp_path):
    html = f'<a href="{TARGET}">Election results</a>'
    first, _, _ = watch(tmp_path, html, 100)
    state, events, _ = watch(tmp_path, "<title>Radware Captcha Page</title>", 160)
    assert state["pages"][URL]["snapshot_sha256"] == first["pages"][URL]["snapshot_sha256"]
    assert state["pages"][URL]["current_candidate_urls"] == first["pages"][URL]["current_candidate_urls"]
    assert not any(e["kind"] == "link_not_observed_this_capture" for e in events)
    state, _, _ = watch(tmp_path, "<title>Access Denied</title>", 220)
    assert state["pages"][URL]["next_check_at"] == 340
    assert TARGET in state["candidates"]


def test_budget_exhaustion_does_not_mark_unchecked_pages_failed(tmp_path):
    def exhausted(url):
        raise RequestBudgetExhausted()

    state, events, summary = run_watch(SEEDS, tmp_path / "state.json", tmp_path / "snapshots",
                                      exhausted, now=100)
    assert not state["pages"] and not events and summary["checked_pages"] == 0


def test_due_selection_does_not_starve_later_seeds(tmp_path):
    seeds = [{"url": f"https://county.gov/{i}", "states": "MI"} for i in range(4)]
    fetched = []

    def capture(url):
        fetched.append(url)
        return url, "<p>Election information</p>"

    for now in (100, 101):
        run_watch(seeds, tmp_path / "state.json", tmp_path / "snapshots", capture,
                  now=now, interval=60, max_pages=2)
    assert len(set(fetched)) == 4


def test_transient_targets_are_not_exported(tmp_path):
    state, _, _ = watch(tmp_path, '<a href="/results?token=secret">Election results</a>', 100)
    assert all("token=" not in url for url in state["candidates"])
    assert "secret" not in (tmp_path / "state.json").read_text()


def test_robots_denies_pages_and_redirects_share_request_budget():
    requested = []

    def transport(request):
        requested.append(str(request.url))
        if request.url.path == "/robots.txt":
            return httpx.Response(200, text="User-agent: *\nDisallow: /private\n",
                                  headers={"content-type": "text/plain"})
        return httpx.Response(302, headers={"location": "/private"})

    fetch = WatchFetcher(delay=0, max_requests=5)
    fetch.client.close()
    fetch.client = httpx.Client(transport=httpx.MockTransport(transport))
    try:
        with pytest.raises(ValueError):
            fetch(URL)
        assert requested == ["https://county.gov/robots.txt", URL]
        assert fetch.requests == 2
    finally:
        fetch.close()


def test_robots_failures_are_unresolved_and_preserve_state(tmp_path):
    fetch = WatchFetcher(delay=0, max_requests=5)
    fetch.client.close()
    fetch.client = httpx.Client(transport=httpx.MockTransport(
        lambda request: httpx.Response(503)))
    try:
        state, _, summary = run_watch(SEEDS, tmp_path / "state.json", tmp_path / "snapshots",
                                      fetch, now=100)
        assert state["pages"][URL]["status"] == "robots_unresolved"
        assert summary["http_requests"] == 1
        assert not state["candidates"]
    finally:
        fetch.close()


def test_crawl_delay_is_scoped_to_declaring_host(monkeypatch):
    sleeps = []
    monkeypatch.setattr("time.sleep", sleeps.append)
    monkeypatch.setattr("time.monotonic", lambda: 100)

    def transport(request):
        if request.url.path == "/robots.txt":
            delay = 30 if request.url.host == "slow.gov" else 1
            return httpx.Response(200, text=f"User-agent: *\nCrawl-delay: {delay}\n",
                                  headers={"content-type": "text/plain"})
        return httpx.Response(200, text="<p>Election information</p>",
                              headers={"content-type": "text/html"})

    fetch = WatchFetcher(delay=1, max_requests=8)
    fetch.client.close()
    fetch.client = httpx.Client(transport=httpx.MockTransport(transport))
    try:
        fetch("https://slow.gov/")
        fetch("https://fast.gov/")
        assert sleeps == [0, 30, 0, 1]
        assert fetch.delay == 1
    finally:
        fetch.close()


def test_worker_lock_prevents_overlapping_state_writes(tmp_path):
    with (worker_lock(tmp_path / "worker.lock"),
          pytest.raises(RuntimeError, match="already owns"),
          worker_lock(tmp_path / "worker.lock")):
        pass


def test_serialized_state_can_be_reloaded(tmp_path):
    state, _, _ = watch(tmp_path, "<p>Election results</p>", 100)
    assert json.loads((tmp_path / "state.json").read_text()) == state


def test_small_budget_does_not_starve_alphabetically_later_states(tmp_path):
    seeds = [{"url": f"https://{s.lower()}.gov/elections", "states": s}
             for s in ("AL", "MI", "WY")]
    visited = []

    def capture(url):
        visited.append(url)
        return url, "<p>Information</p>"

    for now in (100, 160, 220):
        run_watch(seeds, tmp_path / "state.json", tmp_path / "snapshots", capture,
                  now=now, interval=60, max_pages=1)
    assert len(set(visited)) == 3


def test_followup_uses_observed_urls_and_obeys_depth_and_artifact_boundary(tmp_path):
    state, _, _ = watch(tmp_path, f'<a href="{TARGET}">Election results</a>'
                           '<a href="/results.csv">Election results CSV</a>', 100)
    assert len(follow_candidates(SEEDS, state, 0)) == 1
    followed = follow_candidates(SEEDS, state, 1)
    assert any(s["url"] == TARGET for s in followed)
    assert not any(s["url"].endswith(".csv") for s in followed)
