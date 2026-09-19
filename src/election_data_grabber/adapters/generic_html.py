from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime

from bs4 import BeautifulSoup

from election_data_grabber.models import ResultObservation, VoteMode
from election_data_grabber.reporting_unit_identity import AdapterReportingContext, UnitType
from election_data_grabber.vote_modes import normalize_vote_mode


@dataclass(frozen=True, slots=True)
class HtmlTableProfile:
    contest_selector: str | None = None
    reporting_unit_selector: str | None = None


def _state_from_jurisdiction(jurisdiction_id: str) -> str | None:
    parts = jurisdiction_id.lower().split(":")
    if len(parts) >= 2 and parts[0] == "us" and len(parts[1]) == 2:
        return parts[1].upper()
    for state in ("mi", "oh", "pa", "me"):
        if jurisdiction_id.lower().startswith(state + "-"):
            return state.upper()
    return None


def parse_mode_table_html(
    body: bytes,
    *,
    election_id: str,
    jurisdiction_id: str,
    source_id: str,
    fetched_at: datetime,
    profile: HtmlTableProfile = HtmlTableProfile(),
    reporting_context: AdapterReportingContext | None = None,
    reporting_unit_type: UnitType = UnitType.REPORTING_UNIT,
) -> list[ResultObservation]:
    if reporting_context is not None:
        reporting_context.validate_call(election_id=election_id, source_id=source_id)
    soup = BeautifulSoup(body, "html.parser")
    reporting_unit = jurisdiction_id
    if profile.reporting_unit_selector:
        node = soup.select_one(profile.reporting_unit_selector)
        if node:
            reporting_unit = " ".join(node.stripped_strings)

    state = _state_from_jurisdiction(reporting_context.jurisdiction_id if reporting_context else jurisdiction_id)
    observations: list[ResultObservation] = []
    for table in soup.find_all("table"):
        rows = table.find_all("tr")
        if not rows:
            continue
        headers = [" ".join(x.stripped_strings).strip() for x in rows[0].find_all(["th", "td"])]
        mode_cols: dict[int, tuple[VoteMode, str, object | None]] = {}
        for i, header in enumerate(headers):
            resolution = normalize_vote_mode(header, state=state, source_id=source_id)
            if resolution.vote_mode is not None:
                mode_cols[i] = (resolution.vote_mode, header, resolution.rule)
        if not mode_cols:
            continue
        for row in rows[1:]:
            cells = [" ".join(x.stripped_strings).strip() for x in row.find_all(["th", "td"])]
            if len(cells) < 2:
                continue
            choice = cells[0]
            if not choice:
                continue
            contest = table.get("data-contest") or (profile.contest_selector and soup.select_one(profile.contest_selector))
            if hasattr(contest, "stripped_strings"):
                contest = " ".join(contest.stripped_strings)
            contest_name = str(contest or "unknown contest")
            for idx, (mode, raw_label, rule) in mode_cols.items():
                if idx >= len(cells):
                    continue
                m = re.search(r"-?\d[\d,]*", cells[idx])
                if not m:
                    continue
                observations.append(ResultObservation(
                    election_id=election_id,
                    jurisdiction_id=(reporting_context.jurisdiction_id if reporting_context else jurisdiction_id),
                    reporting_unit_id=(reporting_context.unit_id(reporting_unit_type, reporting_unit) if reporting_context else f"{jurisdiction_id}:{reporting_unit}"),
                    reporting_unit_name=reporting_unit,
                    reporting_regime_id=(reporting_context.regime_id if reporting_context else None),
                    reporting_unit_raw_name=(reporting_unit if reporting_context else None),
                    snapshot_sha256=(reporting_context.snapshot_sha256 if reporting_context else None),
                    contest_name=contest_name,
                    choice_name=choice,
                    votes=int(m.group(0).replace(",", "")),
                    vote_mode=mode,
                    source_id=source_id,
                    fetched_at=fetched_at,
                    raw_vote_mode=raw_label,
                    vote_mode_mapping_method=(rule.mapping_method if rule else None),
                    vote_mode_evidence_reference=(rule.evidence_reference if rule else None),
                ))
    return observations
