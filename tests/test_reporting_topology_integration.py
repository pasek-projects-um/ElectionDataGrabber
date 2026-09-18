from datetime import date, datetime, timezone

import pytest

from election_data_grabber.adapters.generic_csv import parse_generic_precinct_csv
from election_data_grabber.adapters.generic_json import parse_generic_results_json
from election_data_grabber.adapters.ohio_precinct_detail import OhioPrecinctDetailAdapter
from election_data_grabber.adapters.washtenaw import WashtenawAdapter
from election_data_grabber.models import Format, Source, SourceKind
from election_data_grabber.reporting_unit_identity import (
    AdapterReportingContext,
    GeographicRelationshipType,
    ReportingUnitGeographicCrosswalk,
    UnitType,
    reporting_regime_id,
    validate_reporting_unit_geographic_crosswalks,
)

SHA="a"*64
NOW=datetime(2026,9,18,tzinfo=timezone.utc)

def source(state,jurisdiction,url="https://example.gov/results"):
    return Source(source_id="fixture-source",jurisdiction=jurisdiction,state=state,url=url,kind=SourceKind.OFFICIAL_WEB,format=Format.HTML,official=True)

def ctx(state,jid,aid,cap="final",kind="certified"):
    return AdapterReportingContext(state,"2024-general",jid,aid,"fixture-source",cap,kind,SHA)

def test_washtenaw_election_night_and_certified_regimes_do_not_collide():
    a=ctx("MI","us:mi:county:washtenaw","us:authority:mi:county-clerk:washtenaw-county-clerk","election_night","election-night")
    b=ctx("MI","us:mi:county:washtenaw","us:authority:mi:county-clerk:washtenaw-county-clerk","final","certified")
    assert a.regime_id != b.regime_id
    assert a.unit_id(UnitType.PRECINCT,"Precinct 1","1") != b.unit_id(UnitType.PRECINCT,"Precinct 1","1")

def test_ohio_precinct_detail_preserves_raw_and_source_native_identity():
    html=b"<table><tr><td>Precinct</td><td>001</td></tr><tr><td>Mayor</td></tr><tr><td>Alice</td><td>12</td></tr></table>"
    context=ctx("OH","us:oh:county:franklin","us:authority:oh:board-of-elections:franklin-county-board-of-elections")
    rows=OhioPrecinctDetailAdapter(source("OH","legacy-franklin"),"2024-general").parse(html,NOW,reporting_context=context)
    assert rows
    r=rows[0]
    assert r.jurisdiction_id == "us:oh:county:franklin"
    assert r.reporting_regime_id == context.regime_id
    assert r.reporting_unit_raw_name == "001"
    assert r.reporting_unit_source_native_id == "001"
    assert r.reporting_unit_id.startswith("us:oh:election:2024-general:reporting-unit:precinct:")

def test_pa_generic_precinct_source_uses_canonical_reporting_context():
    body=b"precinct,contest,candidate,total,mail\nDIV 01,Mayor,Alice,10,4\n"
    context=ctx("PA","us:pa:county:philadelphia","us:authority:pa:county-election-office:philadelphia-county-election-office")
    rows=parse_generic_precinct_csv(body,election_id="2024-general",jurisdiction_id="legacy",source_id="fixture-source",fetched_at=NOW,reporting_context=context)
    assert {r.reporting_regime_id for r in rows} == {context.regime_id}
    assert all(r.reporting_unit_raw_name == "DIV 01" for r in rows)
    assert all(r.reporting_unit_source_native_id == "DIV 01" for r in rows)

def test_maine_ward_reporting_units_do_not_change_primary_locality_identity():
    payload={"reporting_units":[{"id":"ward-2","name":"Ward 2","contests":[{"name":"Council","choices":[{"name":"A","votes":3}]}]}]}
    context=ctx("ME","us:me:municipality:portland","us:authority:me:municipal-clerk:portland-municipal-clerk")
    rows=parse_generic_results_json(payload,election_id="2024-general",jurisdiction_id="legacy",source_id="fixture-source",fetched_at=NOW,reporting_context=context)
    assert rows[0].jurisdiction_id == "us:me:municipality:portland"
    assert "reporting-unit:precinct" in rows[0].reporting_unit_id
    assert rows[0].reporting_unit_source_native_id == "ward-2"

def test_geography_crosswalk_allows_zero_one_many_without_fake_allocation():
    synthetic=ReportingUnitGeographicCrosswalk("ru:avcb",None,GeographicRelationshipType.SYNTHETIC_NON_GEOGRAPHIC,"source",SHA)
    exact=ReportingUnitGeographicCrosswalk("ru:p1","geo:precinct:1",GeographicRelationshipType.EXACT,"source",SHA)
    split1=ReportingUnitGeographicCrosswalk("ru:p2","geo:ward:1",GeographicRelationshipType.SPLIT_ACROSS,"source",SHA)
    split2=ReportingUnitGeographicCrosswalk("ru:p2","geo:ward:2",GeographicRelationshipType.SPLIT_ACROSS,"source",SHA)
    validate_reporting_unit_geographic_crosswalks([synthetic,exact,split1,split2])

def test_geography_crosswalk_rejects_fake_precinct_and_conflicting_temporal_semantics():
    with pytest.raises(ValueError):
        ReportingUnitGeographicCrosswalk("ru:avcb","geo:p1",GeographicRelationshipType.SYNTHETIC_NON_GEOGRAPHIC,"source",SHA)
    a=ReportingUnitGeographicCrosswalk("ru:p1","geo:p1",GeographicRelationshipType.EXACT,"source",SHA,effective_from=date(2024,1,1))
    b=ReportingUnitGeographicCrosswalk("ru:p1","geo:p1",GeographicRelationshipType.APPROXIMATE,"source",SHA,effective_from=date(2024,6,1))
    with pytest.raises(ValueError):
        validate_reporting_unit_geographic_crosswalks([a,b])

def test_allocation_weight_requires_evidence_basis():
    with pytest.raises(ValueError):
        ReportingUnitGeographicCrosswalk("ru:p2","geo:ward:1",GeographicRelationshipType.SPLIT_ACROSS,"source",SHA,allocation_weight=.5)
