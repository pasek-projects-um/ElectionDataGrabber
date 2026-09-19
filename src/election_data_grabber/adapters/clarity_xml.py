from __future__ import annotations

from datetime import datetime
from xml.etree import ElementTree as ET

from election_data_grabber.models import ResultObservation, VoteMode
from election_data_grabber.reporting_unit_identity import AdapterReportingContext, UnitType
from election_data_grabber.vote_modes import normalize_vote_mode


def _text(node: ET.Element | None, *names: str) -> str | None:
    if node is None:
        return None
    for name in names:
        child = node.find(name)
        if child is not None and child.text:
            return child.text.strip()
        if name in node.attrib and node.attrib[name]:
            return node.attrib[name].strip()
    return None


def _state_from_jurisdiction(jurisdiction_id: str) -> str | None:
    parts = jurisdiction_id.lower().split(":")
    if len(parts) >= 2 and parts[0] == "us" and len(parts[1]) == 2:
        return parts[1].upper()
    for state in ("mi", "oh", "pa", "me"):
        if jurisdiction_id.lower().startswith(state + "-"):
            return state.upper()
    return None


def parse_clarity_like_xml(
    body: bytes,
    *,
    election_id: str,
    jurisdiction_id: str,
    source_id: str,
    fetched_at: datetime,
    reporting_context: AdapterReportingContext | None = None,
) -> list[ResultObservation]:
    """Parse a compact Clarity-like XML fixture shape into canonical observations."""
    if reporting_context is not None:
        reporting_context.validate_call(election_id=election_id, source_id=source_id)
    root = ET.fromstring(body)
    observations: list[ResultObservation] = []
    state = _state_from_jurisdiction(reporting_context.jurisdiction_id if reporting_context else jurisdiction_id)

    for precinct in root.findall('.//Precinct'):
        precinct_id = _text(precinct, 'id', 'Id', 'precinctId') or _text(precinct, 'Name')
        precinct_name = _text(precinct, 'name', 'Name') or precinct_id
        if not precinct_id or not precinct_name:
            continue
        for contest in precinct.findall('./Contest'):
            contest_name = _text(contest, 'name', 'Name') or ''
            if not contest_name:
                continue
            for choice in contest.findall('./Choice'):
                choice_name = _text(choice, 'name', 'Name') or ''
                if not choice_name:
                    continue
                party = _text(choice, 'party', 'Party')
                order_raw = _text(choice, 'order', 'Order')
                order = int(order_raw) if order_raw and order_raw.isdigit() else None
                for total in choice.findall('./Total'):
                    mode_raw = _text(total, 'mode', 'Mode') or 'total'
                    resolution = normalize_vote_mode(mode_raw, state=state, source_id=source_id)
                    mode = resolution.vote_mode or VoteMode.UNKNOWN
                    votes_raw = _text(total, 'votes', 'Votes') or '0'
                    observations.append(
                        ResultObservation(
                            election_id=election_id,
                            jurisdiction_id=(reporting_context.jurisdiction_id if reporting_context else jurisdiction_id),
                            reporting_unit_id=(reporting_context.unit_id(UnitType.PRECINCT, precinct_name, precinct_id) if reporting_context else f'{jurisdiction_id}:{precinct_id}'),
                            reporting_unit_name=precinct_name,
                            reporting_regime_id=(reporting_context.regime_id if reporting_context else None),
                            reporting_unit_raw_name=(precinct_name if reporting_context else None),
                            reporting_unit_source_native_id=(precinct_id if reporting_context else None),
                            snapshot_sha256=(reporting_context.snapshot_sha256 if reporting_context else None),
                            contest_name=contest_name,
                            choice_name=choice_name,
                            source_order=order,
                            party=party,
                            votes=int(votes_raw.replace(',', '')),
                            vote_mode=mode,
                            source_id=source_id,
                            fetched_at=fetched_at,
                            raw_vote_mode=mode_raw,
                            vote_mode_mapping_method=(resolution.rule.mapping_method if resolution.rule else None),
                            vote_mode_evidence_reference=(resolution.rule.evidence_reference if resolution.rule else None),
                        )
                    )
    return observations
