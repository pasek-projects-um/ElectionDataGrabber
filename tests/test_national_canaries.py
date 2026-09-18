import csv
from pathlib import Path

import pytest

from election_data_grabber.authority_identity import (
    AuthorityJurisdictionCrosswalk,
    election_authority_id,
    validate_crosswalks,
)
from election_data_grabber.canonical_ids import jurisdiction_id

ROOT = Path(__file__).resolve().parents[1]

# Small deterministic structural sample. These are deliberately not live crawls:
# CI should exercise national identity/authority contracts without depending on
# dozens or hundreds of external election sites.
CASES = [
    ("MI", "county", "Washtenaw", "county", "Washtenaw County Clerk"),
    ("OH", "county", "Franklin", "board_of_elections", "Franklin County Board of Elections"),
    ("ME", "municipality", "Portland", "municipal_clerk", "Portland City Clerk"),
    ("CT", "town", "Greenwich", "town_clerk", "Greenwich Town Clerk"),
    ("PA", "county", "Philadelphia", "county_elections", "Philadelphia City Commissioners"),
    ("LA", "parish", "Orleans", "parish_clerk", "Orleans Parish Clerk"),
    ("VA", "county_equivalent", "Richmond City", "local_electoral_board", "Richmond Electoral Board"),
    ("WI", "municipality", "Madison", "municipal_clerk", "Madison City Clerk"),
    ("NY", "county", "New York", "board_of_elections", "New York City Board of Elections"),
    ("AK", "state", "Alaska", "state_elections", "Alaska Division of Elections"),
    ("ND", "county", "Cass", "county_elections", "Cass County Elections"),
    ("HI", "county_equivalent", "Honolulu", "state_elections", "Hawaii Office of Elections"),
]


@pytest.mark.parametrize("state,level,name,authority_kind,authority_name", CASES)
def test_national_identity_canaries(state, level, name, authority_kind, authority_name):
    jid = jurisdiction_id(state, level, name)
    aid = election_authority_id(state, authority_kind, authority_name)
    row = AuthorityJurisdictionCrosswalk(aid, jid)
    validate_crosswalks([row])
    assert jid.startswith(f"us:{state.lower()}:")
    assert aid.startswith(f"us:authority:{state.lower()}:")


def test_nyc_authority_can_span_multiple_counties():
    aid = election_authority_id("NY", "board_of_elections", "New York City Board of Elections")
    rows = [
        AuthorityJurisdictionCrosswalk(aid, jurisdiction_id("NY", "county", "New York")),
        AuthorityJurisdictionCrosswalk(aid, jurisdiction_id("NY", "county", "Kings")),
    ]
    validate_crosswalks(rows)
    assert len({r.authority_id for r in rows}) == 1


def test_directory_profiles_cover_decentralized_and_centralized_models():
    with (ROOT / "registry/us_state_directory_profiles.csv").open(newline="") as f:
        rows = {row["state"]: row for row in csv.DictReader(f)}
    assert rows["AK"]["profile_type"] == "state_results"
    assert rows["LA"]["profile_type"] == "parish_directory"
    assert rows["MA"]["profile_type"] == "municipal_directory"
    assert rows["WI"]["profile_type"] == "clerk_directory"
