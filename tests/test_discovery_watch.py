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
    clock = [100.0]
    def sleep(seconds):
        sleeps.append(seconds)
        clock[0] += seconds
    monkeypatch.setattr("time.sleep", sleep)
    monkeypatch.setattr("time.monotonic", lambda: clock[0])

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
        assert sum(sleeps) == 31
        assert max(sleeps) <= 0.25
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


def test_deadline_preserves_checkpoint_and_pending_batch(tmp_path, monkeypatch):
    import election_data_grabber.discovery_watch as module
    ticks = iter([0, 0, 10, 10])
    monkeypatch.setattr(module.time, 'monotonic', lambda: next(ticks, 10))
    seeds = SEEDS + [{'url': 'https://other.gov/results', 'states': 'OH'}]
    state, _, summary = run_watch(seeds, tmp_path / 'state.json', tmp_path / 'snapshots',
                                 lambda url: (url, '<p>Election results</p>'),
                                 now=100, interval=60, deadline=5)
    assert summary['checked_pages'] == 1
    assert summary['stop_reason'] == 'time_budget'
    assert summary['remaining_due_pages'] == 1
    assert json.loads((tmp_path / 'state.json').read_text()) == state
    state, _, summary = run_watch(seeds, tmp_path / 'state.json', tmp_path / 'snapshots',
                                 lambda url: (url, '<p>Election results</p>'),
                                 now=101, interval=60, max_pages=1)
    assert summary['checked_pages'] == 1
    assert summary['unvisited_pages'] == 0


def test_budget_exhaustion_does_not_mark_pending_page_checked(tmp_path):
    from election_data_grabber.discovery_watch import TimeBudgetExhausted
    def exhausted(url):
        raise TimeBudgetExhausted()
    state, _, summary = run_watch(SEEDS, tmp_path / 'state.json', tmp_path / 'snapshots',
                                 exhausted, now=100)
    assert not state['pages']
    assert summary['checked_pages'] == 0
    assert summary['remaining_due_pages'] == 1
    assert summary['stop_reason'] == 'time_budget_or_signal'


def test_long_crawl_delay_defers_without_sleeping(monkeypatch):
    from election_data_grabber.discovery_watch import HostDeferred, TimeBudgetExhausted
    fetch = WatchFetcher()
    try:
        monkeypatch.setattr('time.monotonic', lambda: 100)
        fetch.deadline = 200
        fetch.last['county.gov'] = 100
        fetch.host_delays['county.gov'] = 3600
        monkeypatch.setattr('time.sleep', lambda _: pytest.fail('must not sleep'))
        with pytest.raises(HostDeferred):
            fetch.wait_for_host('county.gov')
        fetch.stopping = True
        with pytest.raises(TimeBudgetExhausted):
            fetch.wait_for_host('county.gov')
    finally:
        fetch.close()


def test_deferred_host_does_not_starve_other_hosts(tmp_path):
    from election_data_grabber.discovery_watch import HostDeferred
    seeds = SEEDS + [{'url': 'https://other.gov/results', 'states': 'OH'}]
    def fetch(url):
        if url == URL:
            raise HostDeferred(3600)
        return url, '<p>Election results</p>'
    state, _, summary = run_watch(seeds, tmp_path / 'state.json', tmp_path / 'snapshots',
                                 fetch, now=100)
    assert state['pages'][URL]['next_check_at'] == pytest.approx(3700)
    assert state['pages']['https://other.gov/results']['status'] == 'fetched'
    assert summary['page_statuses'] == {'host_deferred': 1, 'fetched': 1}
    assert summary['live_sources_verified_this_run'] == 0


def test_evidence_archive_and_compact_cache_contract(tmp_path):
    import tarfile

    from scripts.package_watch_evidence import package
    watch(tmp_path / 'state', '<p>Election results</p>', 100)
    manifest = package(tmp_path / 'state', tmp_path / 'artifact')
    with tarfile.open(tmp_path / 'artifact/watch-evidence.tar.gz') as archive:
        names = archive.getnames()
    assert 'state.json' in names
    assert any(name.startswith('snapshots/') for name in names)
    assert any(name.startswith('events/') for name in names)
    assert manifest['files'] == len(names)


def test_deferred_crawl_delay_resumes_across_processes(tmp_path, monkeypatch):
    clock = [10000.0]
    monkeypatch.setattr('time.time', lambda: clock[0])
    monkeypatch.setattr('time.monotonic', lambda: clock[0])
    requested = []
    def transport(request):
        requested.append(str(request.url))
        if request.url.path == '/robots.txt':
            return httpx.Response(200, text='User-agent: *\nCrawl-delay: 3600\n')
        return httpx.Response(200, text='<p>Election results</p>',
                              headers={'content-type': 'text/html'})
    def make_fetch():
        fetch = WatchFetcher()
        fetch.client.close()
        fetch.client = httpx.Client(transport=httpx.MockTransport(transport))
        return fetch
    first = make_fetch()
    try:
        state, _, _ = run_watch(SEEDS, tmp_path / 'state.json', tmp_path / 'snapshots',
                               first, now=clock[0], deadline=clock[0] + 480)
    finally:
        first.close()
    assert state['pages'][URL]['status'] == 'host_deferred'
    assert requested == ['https://county.gov/robots.txt']
    clock[0] += 3601
    second = make_fetch()
    try:
        state, _, summary = run_watch(SEEDS, tmp_path / 'state.json', tmp_path / 'snapshots',
                                     second, now=clock[0], deadline=clock[0] + 480)
    finally:
        second.close()
    assert state['pages'][URL]['status'] == 'fetched'
    assert requested == ['https://county.gov/robots.txt', URL]
    assert summary['http_requests'] == 1


def test_termination_during_host_wait_exports_checkpoint(tmp_path, monkeypatch):
    fetch = WatchFetcher()
    clock = [100.0]
    monkeypatch.setattr('time.monotonic', lambda: clock[0])
    fetch.last['county.gov'] = 100
    fetch.host_delays['county.gov'] = 30
    def stop(seconds):
        fetch.stopping = True
        clock[0] += seconds
    monkeypatch.setattr('time.sleep', stop)
    try:
        state, _, summary = run_watch(SEEDS, tmp_path / 'state.json', tmp_path / 'snapshots',
                                     fetch, now=100, deadline=580)
    finally:
        fetch.close()
    assert summary['stop_reason'] == 'time_budget_or_signal'
    assert summary['http_requests'] == 0
    assert summary['unvisited_pages'] == 1
    assert json.loads((tmp_path / 'state.json').read_text()) == state
