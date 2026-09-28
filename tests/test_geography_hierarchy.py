import pytest
from election_data_grabber.geography_hierarchy import (
    GeographyEdge, GeographyRelation, validate_acyclic_reporting
)

def test_containment_does_not_imply_additivity():
    with pytest.raises(ValueError):
        GeographyEdge("county","city",GeographyRelation.CONTAINS,additive=True)

def test_reporting_cycle_rejected():
    edges=[
        GeographyEdge("county","city",GeographyRelation.REPORTS_TO),
        GeographyEdge("city","county",GeographyRelation.REPORTS_TO),
    ]
    with pytest.raises(ValueError):
        validate_acyclic_reporting(edges)

def test_city_and_county_can_both_report_without_sum_assumption():
    edges=[
        GeographyEdge("county","city",GeographyRelation.CONTAINS),
        GeographyEdge("state","county",GeographyRelation.REPORTS_TO,additive=None),
        GeographyEdge("state","city",GeographyRelation.REPORTS_TO,additive=None),
    ]
    validate_acyclic_reporting(edges)
