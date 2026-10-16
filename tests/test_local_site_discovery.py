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


def test_bad_lead_does_not_stop_valid_fetch_or_next_pass(tmp_path, monkeypatch):
    import csv
    import json
    import sys

    import scripts.watch_national_results as command
    from election_data_grabber.local_site_discovery import FIELDS

    registry = tmp_path / "registry"
    registry.mkdir()
    (registry / "us_primary_election_localities.csv").write_text(
        "jurisdiction_id,state\nus:mi:alpha,MI\n")
    ledger = registry / "local_site_discovery_leads.csv"
    with ledger.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows([lead(), lead(url="https://bad.gov/?token=secret")])
    seeds = tmp_path / "seeds.csv"
    seeds.write_text("url,states\n")
    requested = []

    class Capture:
        def __init__(self, *args, **kwargs):
            self.requests = 0

        def __call__(self, url):
            requested.append(url)
            self.requests += 1
            return url, "<p>Election information</p>"

        def close(self):
            pass

    worker = tmp_path / "worker"
    monkeypatch.setattr(command, "WatchFetcher", Capture)
    monkeypatch.setattr(sys, "argv", ["watch", "--registry", str(registry),
        "--seeds", str(seeds), "--source-seeds", str(tmp_path / "missing.csv"),
        "--state-dir", str(worker)])
    command.main()
    command.main()
    assert requested == ["https://alpha.gov/elections"]
    report = (worker / "quarantined-local-site-leads.csv").read_text()
    assert "secret" not in report and "unsafe_or_unsupported_url" in report
    assert json.loads((worker / "last-run.json").read_text())["quarantined_local_site_leads"] == 1
    assert json.loads((worker / "state.json").read_text())["pages"]


def test_incomplete_csv_row_is_quarantined_without_crashing():
    quarantine = []
    seeds, rejected = inspection_seeds([{"url": None, "observed_at": None}], UNITS,
                                        rejected_rows=quarantine)
    assert seeds == [] and rejected == len(quarantine) == 1


def test_http_client_rejected_url_does_not_abort_other_targets(tmp_path):
    import httpx

    def capture(url):
        if "bad.gov" in url:
            raise httpx.InvalidURL("Malformed URL")
        return url, "<p>Election information</p>"

    seeds = [{"url": "https://bad.gov/", "states": "MI"},
             {"url": "https://good.gov/", "states": "MI"}]
    state, _, summary = run_watch(seeds, tmp_path / "state.json", tmp_path / "snapshots",
                                  capture, now=100)
    assert summary["checked_pages"] == 2
    assert state["pages"]["https://bad.gov/"]["failure_class"] == "InvalidURL"
    assert state["pages"]["https://good.gov/"]["status"] == "fetched"
