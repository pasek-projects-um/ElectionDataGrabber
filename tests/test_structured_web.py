from election_data_grabber.adapters.structured_web import (
    artifact_kind,
    rank_structured_artifacts,
    select_structured_artifact,
)


def test_json_api_is_preferred_over_archive():
    selected=select_structured_artifact([
        "https://x.gov/results.zip",
        "https://x.gov/api/results.json",
    ])
    assert selected is not None
    assert selected.kind=="json"


def test_precinct_detail_breaks_same_kind_tie():
    ranked=rank_structured_artifacts([
        "https://x.gov/data.json",
        "https://x.gov/precinct-results.json",
    ])
    assert ranked[0].url.endswith("precinct-results.json")


def test_unknown_assets_are_not_selected():
    assert artifact_kind("https://x.gov/app.js")=="unknown"
    assert select_structured_artifact(["https://x.gov/app.js"]) is None
