from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from election_data_grabber.adapters.generic_csv import parse_generic_precinct_csv
from election_data_grabber.adapters.generic_json import parse_generic_results_json
from election_data_grabber.identity_aliases import IdentityAlias, resolve_alias, IdentityObjectType
from election_data_grabber.models import ReportingProgress, ResultObservation, Snapshot
from election_data_grabber.provenance import require_snapshot_provenance, validate_snapshot
from election_data_grabber.reconcile import aggregate_observations
from election_data_grabber.reporting_progress import validate_progress_history
from election_data_grabber.reporting_unit_identity import AdapterReportingContext, UnitType
from election_data_grabber.source_capabilities import CapabilityType, JurisdictionSourceCapability, VerificationStatus


@dataclass(frozen=True, slots=True)
class ReplayFixture:
    state: str
    election_id: str
    jurisdiction_id: str
    authority_id: str
    source_id: str
    capability_type: CapabilityType
    regime_kind: str
    format: str
    body_path: Path
    fetched_at: datetime
    source_url: str
    reporting_unit_type: UnitType = UnitType.PRECINCT
    verification_status: VerificationStatus = VerificationStatus.VERIFIED


@dataclass(frozen=True, slots=True)
class ReplayOutput:
    observations: tuple[dict, ...]
    progress: tuple[dict, ...]
    digest: str


def snapshot_for_fixture(fixture: ReplayFixture) -> Snapshot:
    body=fixture.body_path.read_bytes()
    digest=hashlib.sha256(body).hexdigest()
    snapshot=Snapshot(
        source_id=fixture.source_id,
        fetched_at=fixture.fetched_at,
        url=fixture.source_url,
        http_status=200,
        sha256=digest,
        body_path=str(fixture.body_path),
    )
    validate_snapshot(snapshot)
    return snapshot


def _context(fixture: ReplayFixture, snapshot: Snapshot) -> AdapterReportingContext:
    capability=JurisdictionSourceCapability(
        jurisdiction_id=fixture.jurisdiction_id,
        authority_id=fixture.authority_id,
        source_id=fixture.source_id,
        capability_type=fixture.capability_type,
        source_url=fixture.source_url,
        evidence_snapshot_sha256=snapshot.sha256,
        verification_status=fixture.verification_status,
        assessment_method="deterministic_replay_fixture",
        evidence_reference=str(fixture.body_path),
    )
    return AdapterReportingContext.from_source_capability(
        state=fixture.state,
        election_id=fixture.election_id,
        regime_kind=fixture.regime_kind,
        snapshot_sha256=snapshot.sha256,
        capability=capability,
    )


def _parse(fixture: ReplayFixture, snapshot: Snapshot) -> list[ResultObservation]:
    context=_context(fixture,snapshot)
    body=fixture.body_path.read_bytes()
    if fixture.format == "csv":
        return parse_generic_precinct_csv(
            body,election_id=fixture.election_id,jurisdiction_id=fixture.jurisdiction_id,
            source_id=fixture.source_id,fetched_at=fixture.fetched_at,reporting_context=context,
        )
    if fixture.format == "json":
        return parse_generic_results_json(
            json.loads(body.decode("utf-8")),election_id=fixture.election_id,
            jurisdiction_id=fixture.jurisdiction_id,source_id=fixture.source_id,
            fetched_at=fixture.fetched_at,reporting_context=context,
            reporting_unit_type=fixture.reporting_unit_type,
        )
    raise ValueError(f"unsupported deterministic replay fixture format: {fixture.format}")


def _canonical_records(records: list[object]) -> tuple[dict, ...]:
    payload=[]
    for record in records:
        if hasattr(record,"model_dump"):
            item=record.model_dump(mode="json")
        else:
            raise TypeError(f"unsupported replay record: {type(record)!r}")
        payload.append(item)
    return tuple(sorted(payload,key=lambda item: json.dumps(item,sort_keys=True,separators=(",",":"))))


def validate_replay_identity(alias_rows: list[IdentityAlias], *, object_type: IdentityObjectType, namespace: str, value: str) -> str:
    resolved=resolve_alias(alias_rows,object_type=object_type,namespace=namespace,value=value)
    if resolved is None:
        raise ValueError(f"identity unresolved or ambiguous: {object_type}:{namespace}:{value}")
    return resolved


def replay_fixture(
    fixture: ReplayFixture,
    *,
    progress: list[ReportingProgress] | None = None,
    expected_snapshot_sha256: str | None = None,
) -> ReplayOutput:
    snapshot=snapshot_for_fixture(fixture)
    if expected_snapshot_sha256 is not None and snapshot.sha256 != expected_snapshot_sha256:
        raise ValueError("fixture bytes disagree with expected immutable snapshot SHA-256")
    observations=_parse(fixture,snapshot)
    require_snapshot_provenance(observations)
    if any(row.source_id != snapshot.source_id or row.snapshot_sha256 != snapshot.sha256 for row in observations):
        raise ValueError("canonical observation provenance disagrees with immutable snapshot")

    # Integrity checks execute before any canonical output is serialized.
    aggregate_observations(observations)
    if fixture.regime_kind == "election-night" and fixture.capability_type != CapabilityType.ELECTION_NIGHT:
        raise ValueError("election-night replay requires election-night source capability")
    if fixture.regime_kind in {"certified","final"} and fixture.capability_type != CapabilityType.FINAL:
        raise ValueError("final/certified replay requires final source capability")
    progress_rows=list(progress or [])
    if progress_rows:
        require_snapshot_provenance(progress_rows)
        if any(row.source_id != snapshot.source_id or row.snapshot_sha256 != snapshot.sha256 for row in progress_rows):
            raise ValueError("reporting progress provenance disagrees with immutable snapshot")
        findings=validate_progress_history(progress_rows)
        if findings:
            raise ValueError("reporting progress integrity failed: "+"; ".join(findings))

    canonical_observations=_canonical_records(observations)
    canonical_progress=_canonical_records(progress_rows)
    encoded=json.dumps(
        {"observations":canonical_observations,"progress":canonical_progress},
        sort_keys=True,separators=(",",":"),
    ).encode("utf-8")
    return ReplayOutput(canonical_observations,canonical_progress,hashlib.sha256(encoded).hexdigest())


def persist_replay_output(root: Path, output: ReplayOutput) -> Path:
    root.mkdir(parents=True,exist_ok=True)
    target=root/"canonical_replay.json"
    payload={
        "digest":output.digest,
        "observations":output.observations,
        "progress":output.progress,
    }
    target.write_text(json.dumps(payload,sort_keys=True,separators=(",",":"))+"\n",encoding="utf-8")
    return target
