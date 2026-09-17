from datetime import date
import pytest
from election_data_grabber.authority_identity import (
    AuthorityJurisdictionCrosswalk, election_authority_id, validate_crosswalks,
)

def test_authority_identity_does_not_depend_on_jurisdiction():
    aid=election_authority_id("NY","board_of_elections","New York City Board of Elections")
    assert aid=="us:authority:ny:board-of-elections:new-york-city-board-of-elections"

def test_one_authority_can_serve_multiple_jurisdictions():
    aid=election_authority_id("NY","board","NYC BOE")
    rows=[
        AuthorityJurisdictionCrosswalk(aid,"us:ny:county:new-york"),
        AuthorityJurisdictionCrosswalk(aid,"us:ny:county:kings"),
    ]
    validate_crosswalks(rows)
    assert len({r.authority_id for r in rows})==1

def test_relationship_can_change_over_time():
    aid=election_authority_id("XX","board","Example Board")
    rows=[
        AuthorityJurisdictionCrosswalk(aid,"us:xx:municipality:alpha",date(2000,1,1),date(2019,12,31)),
        AuthorityJurisdictionCrosswalk(aid,"us:xx:municipality:alpha",date(2020,1,1),None),
    ]
    validate_crosswalks(rows)
    assert rows[0].active_on(date(2010,1,1))
    assert not rows[0].active_on(date(2021,1,1))

def test_overlapping_relationship_periods_fail():
    aid=election_authority_id("XX","board","Example Board")
    rows=[
        AuthorityJurisdictionCrosswalk(aid,"us:xx:municipality:alpha",date(2000,1,1),date(2020,1,1)),
        AuthorityJurisdictionCrosswalk(aid,"us:xx:municipality:alpha",date(2020,1,1),None),
    ]
    with pytest.raises(ValueError):
        validate_crosswalks(rows)
