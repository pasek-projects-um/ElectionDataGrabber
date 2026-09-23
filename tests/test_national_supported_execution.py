import csv
from pathlib import Path

import scripts.run_national_supported_execution as mod


def _write_manifest(path: Path):
    rows = [
        {
            "state": "MI",
            "result_url": "https://example.test/results.csv",
            "access_family": "tabular_download",
            "parser": "election_data_grabber.adapters.generic_csv:parse_generic_precinct_csv",
            "smallest_observed_unit": "precinct",
            "status": "supported_unverified",
        },
        {
            "state": "WV",
            "result_url": "https://example.test/clarity/",
            "access_family": "clarity",
            "parser": "election_data_grabber.adapters.clarity:discover_clarity_downloads",
            "smallest_observed_unit": "precinct",
            "status": "supported_unverified",
        },
    ]
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)


def test_runner_emits_normalized_and_failure_rows(tmp_path, monkeypatch):
    manifest = tmp_path / "manifest.csv"
    output = tmp_path / "execution.csv"
    _write_manifest(manifest)

    bodies = {
        "https://example.test/results.csv": (
            b"precinct,office,candidate,total\nP1,Mayor,Alice,12\n"
        ),
        "https://example.test/clarity/": b'<a href="detail.xml">Precinct Detail</a>',
    }
    monkeypatch.setattr(mod, "fetch_body", lambda url, timeout: (bodies[url], ""))

    rows = mod.run(manifest, output, timeout=1)
    assert rows[0]["execution_stage"] == "replay_tested"
    assert rows[0]["observation_count"] == "1"
    assert rows[1]["execution_stage"] == "fetchable"
    assert rows[1]["failure_class"] == "requires_download_artifact_selection"
    assert output.exists()


def test_runner_records_fetch_failure(tmp_path, monkeypatch):
    manifest = tmp_path / "manifest.csv"
    output = tmp_path / "execution.csv"
    _write_manifest(manifest)
    monkeypatch.setattr(mod, "fetch_body", lambda url, timeout: (None, "timeout"))

    rows = mod.run(manifest, output, timeout=1, limit=1)
    assert rows == [
        {
            "state": "MI",
            "result_url": "https://example.test/results.csv",
            "access_family": "tabular_download",
            "parser": "election_data_grabber.adapters.generic_csv:parse_generic_precinct_csv",
            "execution_stage": "discovered",
            "observation_count": "0",
            "smallest_observed_unit": "precinct",
            "vote_modes_preserved": "",
            "failure_class": "timeout",
            "snapshot_sha256": "",
        }
    ]
