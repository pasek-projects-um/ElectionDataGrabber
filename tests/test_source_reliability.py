import pytest

from election_data_grabber.source_reliability import (
    canonical_url, load_ledger, merge_source_observation, save_ledger,
)


def test_transient_failure_does_not_erase_verified_coverage(tmp_path):
    initial = merge_source_observation(
        None, jurisdiction_id="us:me:chelsea", source_url="HTTPS://Example.gov/results.pdf#top",
        verified=True, observed_at="2026-10-07T08:00:00Z",
    )
    failed = merge_source_observation(
        initial, jurisdiction_id="us:me:chelsea", source_url="https://example.gov/results.pdf",
        verified=False, observed_at="2026-10-08T08:00:00Z", failure_class="timeout",
    )
    assert failed["ever_verified"] is True
    assert failed["currently_reachable"] is False
    assert failed["last_verified_at"] == initial["last_verified_at"]
    assert failed["last_failure_class"] == "timeout"
    path = tmp_path / "source-ledger.json"
    key = ("us:me:chelsea", "https://example.gov/results.pdf")
    save_ledger(path, {key: failed})
    assert load_ledger(path)[key] == failed
    recovered = merge_source_observation(
        failed, jurisdiction_id=key[0], source_url=key[1],
        verified=True, observed_at="2026-10-09T08:00:00Z",
    )
    assert recovered["currently_reachable"]
    assert recovered["last_failure_class"] == ""
    assert recovered["first_verified_at"] == initial["first_verified_at"]


def test_unverified_source_never_counts_as_verified():
    row = merge_source_observation(
        None, jurisdiction_id="us:me:unknown", source_url="https://example.gov/",
        verified=False, observed_at="2026-10-08T08:00:00Z", failure_class="http_503",
    )
    assert not row["ever_verified"]


def test_rejects_identity_mismatch_and_invalid_evidence():
    row = merge_source_observation(
        None, jurisdiction_id="us:me:a", source_url="https://example.gov/a",
        verified=True, observed_at="2026-10-07T08:00:00Z",
    )
    with pytest.raises(ValueError):
        merge_source_observation(row, jurisdiction_id="us:me:b", source_url="https://example.gov/a",
                                 verified=False, observed_at="2026-10-08T08:00:00Z", failure_class="timeout")
    with pytest.raises(ValueError):
        merge_source_observation(row, jurisdiction_id="us:me:a", source_url="https://example.gov/a",
                                 verified=False, observed_at="2026-10-06T08:00:00Z", failure_class="timeout")
    with pytest.raises(ValueError):
        canonical_url("file:///etc/passwd")


def test_timezone_offsets_and_naive_times_rejected():
    row = merge_source_observation(
        None, jurisdiction_id="us:me:a", source_url="https://example.gov/a",
        verified=True, observed_at="2026-10-08T09:00:00+01:00",
    )
    assert row["last_checked_at"] == "2026-10-08T08:00:00+00:00"
    with pytest.raises(ValueError):
        merge_source_observation(
            row, jurisdiction_id="us:me:a", source_url="https://example.gov/a",
            verified=False, observed_at="2026-10-08T08:30:00",
            failure_class="timeout",
        )


def test_persisted_ledger_rejects_duplicate_source_and_malformed_rows(tmp_path):
    import json
    path = tmp_path / "ledger.json"
    row = merge_source_observation(
        None, jurisdiction_id="us:me:a", source_url="https://example.gov/a",
        verified=True, observed_at="2026-10-08T08:00:00Z",
    )
    path.write_text(json.dumps([row, row]), encoding="utf-8")
    with pytest.raises(ValueError, match="duplicate"):
        load_ledger(path)
    path.write_text(json.dumps([{"jurisdiction_id": "us:me:a", "source_url": "https://example.gov/a", "ever_verified": "yes"}]), encoding="utf-8")
    with pytest.raises(ValueError, match="invalid"):
        load_ledger(path)


def test_url_credentials_are_rejected():
    with pytest.raises(ValueError):
        canonical_url("https://secret:password@example.gov/results")
