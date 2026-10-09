import csv
import httpx

from scripts.national_election_startup_discovery import Seed, allowed_link, crawl_seed, load_seeds, safe_url


class FakeClient:
    def __init__(self, responses):
        self.responses = responses
        self.calls = []

    def get(self, url):
        self.calls.append(url)
        item = self.responses[url]
        if isinstance(item, Exception):
            raise item
        return item


def response(url, html):
    return httpx.Response(200, text=html, headers={"content-type": "text/html"},
                          request=httpx.Request("GET", url))


def test_seed_registry_spans_jurisdiction_levels_and_deduplicates(tmp_path):
    (tmp_path / "us_primary_election_localities.csv").write_text(
        "jurisdiction_id,state,jurisdiction_level,election_night_evidence_url,final_evidence_url\n"
        "us:me:town:a,ME,town,https://town.example/elections,https://town.example/elections\n"
    )
    (tmp_path / "us_state_central_authority_sources.csv").write_text(
        "state,central_authority_url\\nME,https://state.example/elections\n"
    )
    (tmp_path / "us_local_reporting_sources.csv").write_text(
        "state,locality_type,locality_name,authority_url,results_url\n"
        "MI,county,Alpha,https://alpha.example/elections,https://alpha.example/results\n"
    )
    seeds = load_seeds(tmp_path)
    assert len(seeds) == 4
    assert {seed.jurisdiction_level for seed in seeds} == {"town", "county", "state"}


def test_bounded_crawl_prioritizes_result_links_and_restricts_hosts():
    seed = Seed("us:me:town:a", "ME", "town", "https://town.example/elections")
    results = "https://town.example/results"
    other = "https://town.example/voting"
    client = FakeClient({
        seed.url: response(seed.url, '<a href="/voting">Voting</a>'
                          '<a href="/results">Unofficial results</a>'
                          '<a href="https://unrelated.example/results">Elsewhere</a>'),
        results: response(results, ""),
        other: response(other, ""),
    })
    rows = crawl_seed(seed, client, max_pages=2)
    assert [row["url"] for row in rows] == [seed.url, results]
    assert rows[1]["category"] == "result_lead"
    assert not allowed_link(seed.url, "https://unrelated.example/results")


def test_authority_outage_is_not_mistaken_for_missing_dashboard():
    seed = Seed("us:mi:county:alpha", "MI", "county", "https://alpha.example/elections")
    failure = httpx.ConnectError("offline", request=httpx.Request("GET", seed.url))
    rows = crawl_seed(seed, FakeClient({seed.url: failure}))
    assert rows[0]["status"] == "fetch_failed"
    assert rows[0]["error_class"] == "ConnectError"


def test_dangerous_link_types_rejected():
    assert safe_url("javascript:alert(1)") is None
    assert safe_url("mailto:clerk@example.org") is None
    assert safe_url("https://user:password@county.example/results") is None
