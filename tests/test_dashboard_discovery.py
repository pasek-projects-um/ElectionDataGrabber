from pathlib import Path

import httpx
import pytest

from election_data_grabber.national_discovery import (
    Fetcher,
    assess,
    discover,
    load_catalog,
    matches,
    normalize,
    publisher_key,
    run_batch,
)

FIXTURES = Path(__file__).parent / "fixtures/dashboard_discovery"
CLARITY = "https://results.enr.clarityelections.com/MI/Eaton/124075/"
ENHANCED = "https://app.enhancedvoting.com/results/public/example/elections/2026"


def test_catalog_evidence_and_roles():
    catalog = load_catalog()
    assert catalog["version"] == 3
    assert all(r["evidence"] for r in catalog["rules"])
    assert matches("https://evilclarityelections.com/") == []
    assert matches("https://app.enhancedvoting.com.evil.org/") == []
    assert matches("https://county.gov/", "CivicPlus")[0]["role"] == "authority_discovery"


def test_held_out_composition_unlabeled_links_and_cms():
    rows = discover("https://county.gov/elections/", (FIXTURES / "official_links.html").read_text())
    urls = {r["url"]: r for r in rows}
    assert ENHANCED in urls
    assert any(u.startswith(CLARITY) for u in urls)
    assert "https://county.gov/sports/results" not in urls
    cms = urls["https://county.gov/elections/"]
    assert cms["roles"] == ["authority_discovery"] and cms["score"] == 20
    pdf = urls["https://county.gov/archive/2020/report.pdf"]
    assert pdf["roles"] == ["report_family"]
    assert all(r["verification_status"] == "candidate" and not r["live_coverage"] for r in rows)
    # Previous sweep only tests href URL strings against RESULT_RE: these dashboards were missed.
    assert not any("election-results" in u for u in (CLARITY, ENHANCED))


def test_redirects_canonical_and_embedded():
    rows = discover("https://county.gov/", (FIXTURES / "redirects.html").read_text())
    kinds = {p["kind"] for r in rows for p in r["provenance"]}
    assert {"canonical", "meta_redirect", "embedded"} <= kinds
    rows = discover(CLARITY, "<p>Election results</p>", "https://county.gov/current")
    assert "redirect" in {p["kind"] for r in rows for p in r["provenance"]}


@pytest.mark.parametrize(
    "url",
    [
        "javascript:alert(1)",
        "mailto:a@b.com",
        "http://127.0.0.1/",
        "http://localhost/",
        "http://[::1]/",
        "https://a:b@county.gov/",
    ],
)
def test_reject_non_public_targets(url):
    assert normalize(url) == ""


def test_normalization_preserves_tenant_election_and_path():
    assert normalize("https://COUNTY.gov/%65lection-results?year=2020&utm_source=x&tenant=A#x") == (
        "https://county.gov/election-results?tenant=A&year=2020"
    )
    assert normalize("/A%2fb", "https://county.gov/") == "https://county.gov/A%2Fb"
    assert publisher_key(CLARITY + "web.1/") == CLARITY
    assert publisher_key(CLARITY.replace("124075", "123")) != publisher_key(CLARITY)
    assert publisher_key(ENHANCED.replace("example", "other")) != publisher_key(ENHANCED)


def test_context_does_not_verify_live():
    assert (
        assess("Eaton Election results 2024", "Eaton", "2024")["verification_status"]
        == "context_supported"
    )
    assert not assess("Eaton Election results 2024", "Eaton", "2024")["live_coverage"]
    assert (
        assess("Eaton Election results 2020", "Eaton", "2024")["verification_status"]
        == "fetched_unverified"
    )
    assert (
        assess("Eaton Election results 2024", "Other", "2024")["verification_status"]
        == "fetched_unverified"
    )


def test_batch_dedup_resume_and_provenance(tmp_path):
    seeds = [
        {
            "url": "https://county.gov/",
            "jurisdiction_id": j,
            "jurisdiction_name": "Eaton",
            "authority_id": "authority",
            "page_role": "state_directory_fallback",
        }
        for j in ("one", "two")
    ]
    calls = []

    def fetch(url):
        calls.append(url)
        return url, f'<a href="{CLARITY}">View</a><p>Eaton Election results 2024</p>'

    path = tmp_path / "checkpoint.json"
    first = run_batch(seeds, path, fetch, max_requests=1, election="2024")
    assert len(calls) == 1
    assert first["summary"]["candidate_publishers"] == 2
    second = run_batch(seeds, path, fetch, max_requests=1, election="2024")
    assert len(calls) == 2
    assert second["summary"]["verified_live_sources"] == 0
    assert {a["jurisdiction_id"] for a in second["associations"]} == {"one", "two"}
    assert all(not a["served_jurisdiction_verified"] for a in second["associations"])
    assert all(a["source_scope"] == "state_directory_fallback" for a in second["associations"])
    third = run_batch(seeds, path, fetch, max_requests=1, election="2024")
    assert len(calls) == 2
    assert len(third["associations"]) == len(second["associations"])
    with pytest.raises(ValueError, match="mismatch"):
        run_batch(seeds, path, fetch, election="2026")


def test_retry_failure(tmp_path):
    seeds = [{"url": "https://county.gov/", "jurisdiction_id": "one"}]

    def fail(url):
        raise httpx.ConnectError("offline")

    path = tmp_path / "check.json"
    run_batch(seeds, path, fail)
    calls = []

    def ok(url):
        calls.append(url)
        return url, "<p>Election results</p>"

    run_batch(seeds, path, ok)
    assert calls == []
    run_batch(seeds, path, ok, retry_failed=True)
    assert len(calls) == 1


def test_fetcher_redirect_size_and_artifact_limits():
    fetch = Fetcher(delay=0, max_bytes=10)
    fetch.client.close()
    fetch.client = httpx.Client(
        transport=httpx.MockTransport(
            lambda req: httpx.Response(302, headers={"location": "http://127.0.0.1/"})
        )
    )
    with pytest.raises(ValueError, match="Unsafe"):
        fetch("https://county.gov/")
    fetch.client.close()
    fetch.client = httpx.Client(
        transport=httpx.MockTransport(
            lambda req: httpx.Response(
                200, headers={"content-type": "text/html"}, content=b"x" * 11
            )
        )
    )
    with pytest.raises(ValueError, match="byte limit"):
        fetch("https://county.gov/")
    fetch.close()


def test_observed_official_vendor_links_improve_legacy_sweep():
    import json

    from scripts.sweep_national_local_reporting_sources import RESULT_RE

    manifest = json.loads((FIXTURES / "observed-manifest.json").read_text())
    totals = [0, 0]
    for record in manifest:
        html = (FIXTURES / record["fixture"]).read_text()
        rows = discover(record["final_url"], html)
        candidates = {r["url"] for r in rows if "enhanced-public" in r["signatures"]}
        old = {r["url"] for r in rows if RESULT_RE.search(r["url"])}
        assert len(candidates) == record["new_dashboard_candidates"]
        assert len(old) == record["legacy_url_keyword_hits"]
        totals[0] += len(candidates)
        totals[1] += len(old)
    assert totals == [18, 0]


@pytest.mark.parametrize(
    ("text", "family", "role"),
    [
        ("Scytl", "scytl", "result_platform"),
        ("Electionware", "electionware", "report_family"),
        ("CivicPlus", "civicplus", "authority_discovery"),
    ],
)
def test_brand_role_separation(text, family, role):
    hits = matches("https://county.gov/", text)
    assert hits[0]["family"] == family and hits[0]["role"] == role
    assert not discover("https://county.gov/", text)[0]["live_coverage"]


def test_false_positive_controls():
    for html in (
        '<a href="/sports/results">Results</a>',
        "<p>CivicPlus</p>",
        '<a href="/reports/index.pdf">Annual budget</a>',
    ):
        rows = discover("https://county.gov/", html)
        assert not any("result_platform" in r["roles"] for r in rows)


def test_http_request_budget_counts_redirects():
    from election_data_grabber.national_discovery import RequestBudgetExhausted

    fetch = Fetcher(delay=0, max_requests=2)
    fetch.client.close()
    fetch.client = httpx.Client(
        transport=httpx.MockTransport(
            lambda req: httpx.Response(302, headers={"location": "https://county.gov/next"})
        )
    )
    with pytest.raises(RequestBudgetExhausted):
        fetch("https://county.gov/")
    assert fetch.requests == 2
    fetch.close()


def test_context_uses_boundaries_and_rejects_state_abbreviations():
    assert (
        assess("Eatonville Election results 2024", "Eaton", "2024")["verification_status"]
        == "fetched_unverified"
    )
    assert (
        assess("MA Election results 2024", "MA", "2024")["verification_status"]
        == "fetched_unverified"
    )


def test_national_selection_spreads_states(tmp_path):
    seeds = [
        {"url": f"https://{state}{i}.gov/", "jurisdiction_id": f"{state}{i}", "state": state}
        for state in ("AK", "WI")
        for i in range(3)
    ]
    calls = []

    def fetch(url):
        calls.append(url)
        return url, "No results yet"

    result = run_batch(seeds, tmp_path / "state.json", fetch, max_publishers=2)
    assert result["summary"]["selected_states"] == ["AK", "WI"]
    assert calls == ["https://ak0.gov/", "https://wi0.gov/"]


def test_observed_custom_hosts_and_html_base():
    import json

    manifest = json.loads((FIXTURES / "custom-host-manifest.json").read_text())
    for record in manifest:
        rows = discover(record["url"], (FIXTURES / record["fixture"]).read_text())
        root = next(r for r in rows if r["url"] == record["url"])
        assert "enhanced-government-hosts" in root["signatures"]
        script_urls = [
            r["url"] for r in rows if any(p["kind"] == "script" for p in r["provenance"])
        ]
        assert script_urls and all(
            "/results/public/main-" in u or "/results/public/polyfills-" in u for u in script_urls
        )
        assert not root["live_coverage"]
    assert not any(
        r["family"] == "enhanced_voting" for r in matches("https://results.sos.ga.gov.evil.org/")
    )


def test_cms_script_is_not_result_platform():
    rows = discover(
        "https://county.gov/", '<script src="https://assets.civicplus.com/app.js"></script>'
    )
    assert rows[0]["roles"] == ["authority_discovery"]
    assert rows[0]["score"] == 0


def test_artifact_is_an_explicit_uninspected_state(tmp_path):
    from election_data_grabber.national_discovery import ArtifactNeedsInspection

    def artifact(url):
        raise ArtifactNeedsInspection("PDF")

    state = run_batch(
        [{"url": "https://county.gov/report.pdf", "jurisdiction_id": "one"}],
        tmp_path / "artifact.json",
        artifact,
    )
    assert state["pages"]["https://county.gov/report.pdf"]["status"] == "artifact_needs_inspection"


def test_blocked_html_is_not_a_successful_discovery(tmp_path):
    from election_data_grabber.national_discovery import html_access_state

    assert (
        html_access_state(
            "<title>Request Rejected</title>Request Rejected The requested URL was rejected"
        )
        == "blocked_html"
    )
    assert (
        html_access_state("<title>Election Results</title><app-root></app-root>")
        == "application_shell"
    )
    seed = {"url": "https://state.gov/election-results", "jurisdiction_id": "state"}
    state = run_batch(
        [seed],
        tmp_path / "blocked.json",
        lambda url: (
            url,
            "<title>Request Rejected</title>Request Rejected The requested URL was rejected",
        ),
    )
    assert state["pages"][seed["url"]]["status"] == "blocked_html"
    assert state["publishers"] == {}


def test_quest_requires_brand_and_assets():
    rows = discover("https://enr.indianavoters.in.gov/", (FIXTURES / "quest-enr.html").read_text())
    assert (
        "quest-enr-html"
        in next(r for r in rows if r["url"] == "https://enr.indianavoters.in.gov/")["signatures"]
    )
    assert not matches("https://county.gov/", html="<p>Quest Information Systems</p>")


def test_html_fingerprint_handles_large_negative_page():
    # Anchored lookaheads inspect the page once rather than retrying at every character.
    rule = next(r for r in load_catalog()["rules"] if r["id"] == "quest-enr-html")
    assert rule["pattern"].startswith("(?s)^")
    assert not matches("https://county.gov/", html="<p>Budget</p>" * 80000)
