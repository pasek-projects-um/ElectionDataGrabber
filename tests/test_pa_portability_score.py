from scripts.score_pa_portability import summarize

def test_pa_statewide_registry_scoring():
    result=summarize()
    assert result["counties"] == 67
