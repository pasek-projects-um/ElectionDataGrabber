from election_data_grabber.source_overlap import (
    OverlapCalibration, OverlapRelationship, SourceSnapshot,
    comparable_progress, cosine_similarity, jaccard,
)

def test_imperfect_similarity_does_not_imply_independence():
    calibration=OverlapCalibration(
        "a","b","us:aa:county:x",8,0.94,0.80,0.50,
        OverlapRelationship.PARTIAL_OVERLAP,
    )
    assert calibration.safe_for_independent_evidence is False

def test_independence_requires_explicit_establishment():
    calibration=OverlapCalibration(
        "a","b","us:aa:county:x",8,0.70,0.20,0.0,
        OverlapRelationship.COMPLEMENTARY,
        residual_independence_established=True,
    )
    assert calibration.safe_for_independent_evidence is True

def test_progress_matching_is_jurisdiction_scoped():
    a=SourceSnapshot("a","j1","t1",0.50,(0.6,0.4),frozenset({"p1","p2"}))
    b=SourceSnapshot("b","j1","t2",0.53,(0.59,0.41),frozenset({"p2","p3"}))
    c=SourceSnapshot("c","j2","t2",0.53,(0.59,0.41))
    assert comparable_progress(a,b)
    assert not comparable_progress(a,c)
    assert cosine_similarity(a.result_vector,b.result_vector) > 0.99
    assert jaccard(a.reporting_units,b.reporting_units) == 1/3
