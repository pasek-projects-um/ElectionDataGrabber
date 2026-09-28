from __future__ import annotations

import hashlib
from datetime import datetime
from typing import Callable
import json

from election_data_grabber.adapters.enhanced_voting import parse_enhanced_voting_html
from election_data_grabber.adapters.clarity import discover_clarity_downloads, select_clarity_detail_artifact
from election_data_grabber.adapters.clarity_xml import parse_clarity_like_xml
from election_data_grabber.adapters.generic_csv import parse_generic_precinct_csv
from election_data_grabber.adapters.generic_json import parse_generic_results_json
from election_data_grabber.adapters.generic_excel import parse_generic_precinct_excel
from election_data_grabber.execution_maturity import ExecutionStage, SourceExecutionEvidence


PARSER_FUNCTIONS: dict[str, Callable] = {
    "election_data_grabber.adapters.enhanced_voting:parse_enhanced_voting_html": parse_enhanced_voting_html,
    "election_data_grabber.adapters.generic_csv:parse_generic_precinct_csv": parse_generic_precinct_csv,
    "election_data_grabber.adapters.clarity_xml:parse_clarity_like_xml": parse_clarity_like_xml,
    "election_data_grabber.adapters.generic_json:parse_generic_results_json": parse_generic_results_json,
    "election_data_grabber.adapters.generic_excel:parse_generic_precinct_excel": parse_generic_precinct_excel,
}


def snapshot_sha256(body: bytes) -> str:
    return hashlib.sha256(body).hexdigest()


def execute_supported_body(
    manifest_row: dict[str, str],
    body: bytes,
    *,
    election_id: str,
    jurisdiction_id: str,
    source_id: str,
    fetched_at: datetime,
) -> SourceExecutionEvidence:
    parser_path = manifest_row["parser"]
    family = manifest_row["access_family"]

    if family == "clarity":
        surface=discover_clarity_downloads(body,manifest_row["result_url"])
        artifact=select_clarity_detail_artifact(surface)
        return SourceExecutionEvidence(
            state=manifest_row["state"],
            result_url=manifest_row["result_url"],
            access_family=family,
            parser=parser_path,
            stage=(ExecutionStage.PARSER_SELECTED if artifact else ExecutionStage.FETCHABLE),
            smallest_observed_unit=manifest_row.get("smallest_observed_unit", "unknown"),
            snapshot_sha256=snapshot_sha256(body),
            failure_class=("artifact_discovered_requires_fetch" if artifact else "requires_download_artifact_selection"),
        )

    parser = PARSER_FUNCTIONS.get(parser_path)
    if parser is None:
        return SourceExecutionEvidence(
            state=manifest_row["state"],
            result_url=manifest_row["result_url"],
            access_family=family,
            parser=parser_path,
            stage=ExecutionStage.PARSER_SELECTED,
            smallest_observed_unit=manifest_row.get("smallest_observed_unit", "unknown"),
            snapshot_sha256=snapshot_sha256(body),
            failure_class="parser_not_executable",
        )

    payload = body
    if parser is parse_generic_results_json:
        try:
            payload = json.loads(body.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            return SourceExecutionEvidence(
                state=manifest_row["state"],
                result_url=manifest_row["result_url"],
                access_family=family,
                parser=parser_path,
                stage=ExecutionStage.PARSER_SELECTED,
                smallest_observed_unit=manifest_row.get("smallest_observed_unit", "unknown"),
                snapshot_sha256=snapshot_sha256(body),
                failure_class="invalid_json_payload",
            )
    kwargs = {
        "election_id": election_id,
        "jurisdiction_id": jurisdiction_id,
        "source_id": source_id,
        "fetched_at": fetched_at,
    }
    if parser is parse_generic_precinct_excel:
        kwargs["filename"] = manifest_row["result_url"]
    rows = parser(payload, **kwargs)
    if not rows:
        return SourceExecutionEvidence(
            state=manifest_row["state"],
            result_url=manifest_row["result_url"],
            access_family=family,
            parser=parser_path,
            stage=ExecutionStage.PARSE_EXECUTED,
            smallest_observed_unit=manifest_row.get("smallest_observed_unit", "unknown"),
            snapshot_sha256=snapshot_sha256(body),
            failure_class="no_normalized_observations",
        )

    explicit_modes = {getattr(row, "raw_vote_mode", None) for row in rows}
    vote_modes_preserved = bool(explicit_modes - {None, "", "total", "votes"})
    return SourceExecutionEvidence(
        state=manifest_row["state"],
        result_url=manifest_row["result_url"],
        access_family=family,
        parser=parser_path,
        stage=ExecutionStage.REPLAY_TESTED,
        observation_count=len(rows),
        smallest_observed_unit=manifest_row.get("smallest_observed_unit", "unknown"),
        vote_modes_preserved=vote_modes_preserved,
        snapshot_sha256=snapshot_sha256(body),
    )
