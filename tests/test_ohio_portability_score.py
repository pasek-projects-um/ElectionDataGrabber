from pathlib import Path

from scripts.score_ohio_portability import score


def test_first_twenty_ohio_counties_are_mostly_reusable():
    result = score(Path("registry/oh_county_capabilities.csv"))
    assert result["counties"] == 20
    assert result["A"] == 3
    assert result["B"] == 14
    assert result["C"] == 3
    assert result["D"] == 0
    assert result["E"] == 0
    assert result["A_or_B_share"] == 0.85
    assert result["A_B_or_C_share"] == 1.0
