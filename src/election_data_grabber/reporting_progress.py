from __future__ import annotations

from collections.abc import Iterable

from election_data_grabber.models import ReportingProgress, ReportingProgressKind, UpdateSemantics


def validate_progress_history(rows: Iterable[ReportingProgress]) -> list[str]:
    """Return audit findings for progress transitions without rewriting history."""
    findings: list[str] = []
    groups: dict[tuple[str, str, str, str, str | None], list[ReportingProgress]] = {}
    for row in rows:
        key=(
            row.election_id,
            row.jurisdiction_id,
            row.source_id,
            row.scope.value,
            row.reporting_unit_id,
        )
        groups.setdefault(key,[]).append(row)

    for key, group in groups.items():
        ordered=sorted(group,key=lambda r:(r.source_timestamp or r.fetched_at,r.fetched_at))
        prior_reporting: int | None=None
        prior_expected: int | None=None
        prior_complete: bool | None=None
        for row in ordered:
            if row.kind == ReportingProgressKind.SOURCE_COUNTS:
                if (
                    row.update_semantics == UpdateSemantics.CUMULATIVE
                    and prior_reporting is not None
                    and row.reporting_count is not None
                    and row.reporting_count < prior_reporting
                ):
                    findings.append(f"{key}: cumulative reporting_count decreased {prior_reporting}->{row.reporting_count}")
                if prior_expected is not None and row.expected_count is not None and row.expected_count != prior_expected:
                    findings.append(f"{key}: expected_count changed {prior_expected}->{row.expected_count}")
                if row.reporting_count is not None:
                    prior_reporting=row.reporting_count
                if row.expected_count is not None:
                    prior_expected=row.expected_count
            elif row.kind == ReportingProgressKind.SOURCE_COMPLETE:
                if prior_complete is True and row.complete is False:
                    findings.append(f"{key}: source completion regressed true->false")
                if row.complete is not None:
                    prior_complete=row.complete
    return findings
