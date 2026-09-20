from pathlib import Path

from scripts.generate_state_unit_data_access_census import build_census

ROOT=Path(__file__).resolve().parents[1]


def test_state_unit_data_access_census_spans_denominator_states():
    rows=build_census(ROOT)
    by={r["state"]:r for r in rows}
    assert {"MI","OH","CT","PA","ME","WI","MA","GA"}.issubset(by)
    assert by["MI"]["expected_primary_units"]=="83"
    assert by["OH"]["expected_primary_units"]=="88"
    assert by["CT"]["administrative_levels"]=="municipality:169"
    assert by["PA"]["administrative_levels"]=="county:67"


def test_census_separates_admin_reporting_and_access_dimensions():
    rows=build_census(ROOT)
    mi=next(r for r in rows if r["state"]=="MI")
    assert "county:" in mi["administrative_levels"]
    assert "final:" in mi["capability_types"]
    assert mi["observed_reporting_units"] != "none"
    assert mi["data_access_families"] != "none"


def test_unresolved_states_still_show_denominator_even_before_enumeration():
    rows=build_census(ROOT)
    wi=next(r for r in rows if r["state"]=="WI")
    assert wi["expected_primary_units"]=="1850"
    assert int(wi["enumerated_primary_units"]) <= 1850
