import pytest
from election_data_grabber.canonical_ids import authority_id, jurisdiction_id


def test_external_id_is_preferred_and_deterministic():
    assert jurisdiction_id("MD", "county", "Montgomery County", "24031") == "us:md:county:24031"
    assert jurisdiction_id("MD", "county", "RENAMED", "24031") == "us:md:county:24031"


def test_name_fallback_is_normalized():
    assert jurisdiction_id("WI", "municipality", "Fond du Lac") == "us:wi:municipality:fond-du-lac"


def test_authority_is_separate_from_jurisdiction():
    j = jurisdiction_id("NY", "county", "Albany County", "36001")
    assert authority_id(j, "board of elections") == "us:ny:county:36001:authority:board-of-elections:1"


def test_bad_inputs_fail():
    with pytest.raises(ValueError):
        jurisdiction_id("Maryland", "county", "Montgomery")
    with pytest.raises(ValueError):
        jurisdiction_id("MD", "precinct", "1")
