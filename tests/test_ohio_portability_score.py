from pathlib import Path

from scripts.score_ohio_portability import score


def test_statewide_ohio_portability_distribution():
    result = score(Path("registry/oh_county_capabilities.csv"))
    assert result["counties"] == 88
    assert result["A"] == 60
    assert result["B"] == 25
    assert result["C"] == 3
    assert result["D"] == 0
    assert result["E"] == 0
    assert result["A_or_B_share"] == 85 / 88
    assert result["A_B_or_C_share"] == 1.0
