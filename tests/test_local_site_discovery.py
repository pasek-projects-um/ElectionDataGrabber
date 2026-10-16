from election_data_grabber.local_site_discovery import inspection_seeds
from election_data_grabber.discovery_watch import follow_candidates, run_watch

UNITS = [{"jurisdiction_id": "us:mi:alpha", "state": "MI"}]


def lead(**kwargs):
    return dict({"jurisdiction_id": "us:mi:alpha", "state": "MI",
                 "url": "https://alpha.gov/elections", "discovered_from": "https://mi.gov/clerks",
                 "evidence_excerpt": "Alpha County election office website",
                 "observed_at": "2026-10-16T02:00:00Z",
                 "evidence_status": "observed_link_candidate"}, **kwargs)


def test_fresh_search_lead_enters_next_round_and_keeps_followup(tmp_path):
    seeds, rejected = inspection_seeds([lead(), lead()], UNITS)
    assert rejected == 0 and len(seeds) == 1
    state, _, _ = run_watch(seeds, tmp_path / "state.json", tmp_path / "snapshots",
                            lambda url: (url, '<a href="/results">Election results</a>'), now=100)
    follow = follow_candidates(seeds, state, 2)
    result = next(s for s in follow if s["url"] == "https://alpha.gov/results")
    assert result["associated_unit_ids"] == "us:mi:alpha"
    assert seeds[0]["observed_from"] == "https://mi.gov/clerks"
    assert not state["candidates"][result["url"]]["live_coverage"]
    assert seeds[0]["served_jurisdiction_verified"] == "false"


def test_wrong_units_missing_evidence_and_unsafe_urls_are_rejected():
    rows = [lead(jurisdiction_id="unknown"), lead(state="OH"), lead(evidence_excerpt=""),
            lead(observed_at="yesterday"), lead(observed_at="2026-10-16T02:00:00"),
            lead(evidence_status="verified"), lead(url="http://localhost/"),
            lead(url="https://alpha.gov/results.pdf"),
            lead(discovered_from="https://mi.gov/?token=secret")]
    seeds, rejected = inspection_seeds(rows, UNITS)
    assert seeds == [] and rejected == len(rows)
