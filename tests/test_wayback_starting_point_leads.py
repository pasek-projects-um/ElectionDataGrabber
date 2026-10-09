from scripts.wayback_starting_point_leads import archive_candidates, windows


class Response:
    def __init__(self, payload=None, text=""):
        self.payload = payload
        self.text = text

    def raise_for_status(self):
        return None

    def json(self):
        return self.payload


class Client:
    def __init__(self):
        self.params = None

    def get(self, url, params=None):
        if params is not None:
            self.params = params
            return Response([["timestamp", "original", "statuscode"],
                             ["20241106083000", "https://county.example/elections", "200"]])
        return Response(text='<a href="/results/2024">2024 election results</a>')


def test_bounded_2024_general_archive_leads_are_not_current_verified():
    client = Client()
    rows = archive_candidates("us:xx:county:example", "https://county.example/elections",
                              "2024_general", "2024-11-05", client)
    assert len(rows) == 1
    assert rows[0]["original_url"] == "https://county.example/results/2024"
    assert rows[0]["evidence_status"] == "archived_only_unverified_current"
    assert ("filter", "statuscode:200") in client.params
    assert ("filter", "mimetype:text/html") in client.params
    assert ("from", "20241102") in client.params


def test_reject_wrong_election_year():
    import pytest
    with pytest.raises(ValueError):
        windows("2026_primary", "2025-08-05")
