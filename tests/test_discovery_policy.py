from datetime import UTC, datetime

from election_data_grabber.discovery_policy import (
    discovery_frontier,
    monitoring_seeds,
    search_queue,
)

UNITS = [{"jurisdiction_id": "alpha", "state": "MI", "canonical_name": "Alpha"}]


def iso(seconds):
    return datetime.fromtimestamp(seconds, UTC).isoformat()


def lead(url="https://alpha.gov/", when=10):
    return {"jurisdiction_id": "alpha", "state": "MI", "url": url,
            "observed_at": iso(when), "evidence_status": "observed_link_candidate"}


def attempt(when, outcome="completed_no_new_urls"):
    return {"jurisdiction_id": "alpha", "state": "MI", "attempted_at": iso(when),
            "outcome": outcome}


def test_first_lead_does_not_stop_alternative_discovery():
    rows = discovery_frontier(UNITS, [lead()], [], now=100)
    assert rows[0]["discovery_status"] == "active"
    assert search_queue(rows)[0]["jurisdiction_id"] == "alpha"
    rows = discovery_frontier(UNITS, [lead(), lead("https://other.gov/", 30)],
                              [attempt(20)], now=100)
    assert rows[0]["observed_candidate_urls"] == 2
    assert rows[0]["completed_quiet_rounds"] == 0


def test_three_distinct_completed_quiet_rounds_pause_without_claiming_completeness():
    attempts = [attempt(20), attempt(20), attempt(30), attempt(40)]
    rows = discovery_frontier(UNITS, [lead()], attempts, now=100)
    assert rows[0]["completed_quiet_rounds"] == 3
    assert rows[0]["discovery_status"] == "exhausted_for_now"
    assert rows[0]["coverage_complete"] == "false"
    assert search_queue(rows) == []
    assert search_queue(discovery_frontier(UNITS, [lead()], attempts, now=86440))
    # Reobserving the same URL does not count as new evidence.
    rows = discovery_frontier(UNITS, [lead(), lead(when=50)], attempts, now=100)
    assert rows[0]["discovery_status"] == "exhausted_for_now"


def test_blocked_and_incomplete_searches_do_not_count_as_quiet_rounds():
    rows = discovery_frontier(UNITS, [], [attempt(10, "blocked"),
                              attempt(20, "partial"), attempt(30, "no_results")], now=100)
    assert rows[0]["completed_quiet_rounds"] == 0


def test_new_watcher_link_reopens_and_parking_keeps_daily_roots_and_best_candidates():
    attempts = [attempt(20), attempt(30), attempt(40)]
    state = {"pages": {"https://alpha.gov/": {"last_success_at": 50}}, "candidates": {}}
    roots = [{"url": "https://alpha.gov/", "associated_unit_ids": "alpha"}]
    rows = discovery_frontier(UNITS, [lead()], attempts, now=100)
    assert monitoring_seeds(roots, state, rows, now=100) == []
    assert monitoring_seeds(roots, state, rows, now=86450) == roots
    state["candidates"]["https://alpha.gov/results"] = {
        "url": "https://alpha.gov/results", "first_observed_at": 60,
        "seed_associations": [{"associated_unit_ids": "alpha"}]}
    reopened = discovery_frontier(UNITS, [lead()], attempts, now=100, watch_state=state)
    assert reopened[0]["discovery_status"] == "active"
    assert monitoring_seeds(roots, state, reopened, now=100) == roots


def test_paused_unit_does_not_suppress_shared_root_for_active_unit():
    rows = [{"jurisdiction_id": "alpha", "discovery_status": "exhausted_for_now"}]
    seeds = [{"url": "https://state.gov/", "associated_unit_ids": "alpha | beta"}]
    assert monitoring_seeds(seeds, {}, rows, now=100) == seeds
