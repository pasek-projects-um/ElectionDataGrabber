import pytest

from election_data_grabber.execution_maturity import (
    ExecutionStage,
    SourceExecutionEvidence,
    maturity_row,
    promotable_to_supported,
)


def _evidence(stage: ExecutionStage, **overrides):
    values = dict(
        state="MI",
        result_url="https://example.gov/results.csv",
        access_family="tabular_download",
        parser="election_data_grabber.adapters.generic_csv:parse_generic_precinct_csv",
        stage=stage,
        observation_count=0,
        smallest_observed_unit="precinct",
        vote_modes_preserved=None,
        failure_class="",
        snapshot_sha256="",
    )
    values.update(overrides)
    return SourceExecutionEvidence(**values)


@pytest.mark.parametrize(
    ("stage", "promotable"),
    [
        (ExecutionStage.DISCOVERED, False),
        (ExecutionStage.FETCHABLE, False),
        (ExecutionStage.PARSER_SELECTED, False),
        (ExecutionStage.PARSE_EXECUTED, False),
        (ExecutionStage.NORMALIZED, True),
        (ExecutionStage.REPLAY_TESTED, True),
        (ExecutionStage.REFRESH_VERIFIED, True),
    ],
)
def test_supported_promotion_requires_normalized_observations(stage, promotable):
    kwargs = {"observation_count": 12} if stage >= ExecutionStage.NORMALIZED else {}
    if stage >= ExecutionStage.REPLAY_TESTED:
        kwargs["snapshot_sha256"] = "a" * 64
    assert promotable_to_supported(_evidence(stage, **kwargs)) is promotable


def test_replay_requires_snapshot_provenance():
    with pytest.raises(ValueError, match="immutable snapshot"):
        maturity_row(_evidence(ExecutionStage.REPLAY_TESTED, observation_count=4))


def test_normalized_requires_observations():
    with pytest.raises(ValueError, match="requires observations"):
        maturity_row(_evidence(ExecutionStage.NORMALIZED))


def test_failure_class_cannot_coexist_with_normalized_success():
    with pytest.raises(ValueError, match="failure class"):
        maturity_row(
            _evidence(
                ExecutionStage.NORMALIZED,
                observation_count=4,
                failure_class="schema_unrecognized",
            )
        )


def test_manifest_row_is_stable_and_explicit():
    row = maturity_row(
        _evidence(
            ExecutionStage.REPLAY_TESTED,
            observation_count=42,
            vote_modes_preserved=True,
            snapshot_sha256="b" * 64,
        )
    )
    assert row["execution_stage"] == "replay_tested"
    assert row["observation_count"] == "42"
    assert row["vote_modes_preserved"] == "true"
    assert row["snapshot_sha256"] == "b" * 64
