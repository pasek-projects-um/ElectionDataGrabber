from pathlib import Path
from scripts.build_external_corpus_gap_matrix import build_gap_matrix


def test_gap_matrix_has_51_states_and_dc():
    root=Path(__file__).resolve().parents[1]
    rows=build_gap_matrix(root)
    assert len(rows)==51
    assert len({r["state"] for r in rows})==51


def test_every_state_has_at_least_one_concrete_primary_candidate():
    root=Path(__file__).resolve().parents[1]
    rows=build_gap_matrix(root)
    assert all(int(r["official_candidate_count"]) >= 1 for r in rows)
    assert not any(r["secondary_only"]=="true" for r in rows)
