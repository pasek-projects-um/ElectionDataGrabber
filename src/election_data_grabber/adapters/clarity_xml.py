from __future__ import annotations

from datetime import datetime
from xml.etree import ElementTree as ET

from election_data_grabber.models import ResultObservation, VoteMode


_MODE_MAP = {
    "election day": VoteMode.ELECTION_DAY,
    "election_day": VoteMode.ELECTION_DAY,
    "early": VoteMode.EARLY,
    "early voting": VoteMode.EARLY,
    "absentee": VoteMode.ABSENTEE,
    "mail": VoteMode.MAIL,
    "provisional": VoteMode.PROVISIONAL,
    "total": VoteMode.TOTAL,
}


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


def parse_clarity_like_xml(
    body: bytes,
    *,
    election_id: str,
    jurisdiction_id: str,
    source_id: str,
    fetched_at: datetime,
) -> list[ResultObservation]:
    """Parse a compact Clarity-like XML fixture shape into canonical observations.

    Real Clarity deployments vary by export; this is intentionally a compatibility
    contract for tests and a staging point before delegating richer discovery/parsing
    to OpenElections clarify.
    """
    root = ET.fromstring(body)
    observations: list[ResultObservation] = []

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
                    mode_raw = (_text(total, 'mode', 'Mode') or 'total').lower()
                    mode = _MODE_MAP.get(mode_raw, VoteMode.OTHER)
                    votes_raw = _text(total, 'votes', 'Votes') or '0'
                    observations.append(
                        ResultObservation(
                            election_id=election_id,
                            jurisdiction_id=jurisdiction_id,
                            reporting_unit_id=f'{jurisdiction_id}:{precinct_id}',
                            reporting_unit_name=precinct_name,
                            contest_name=contest_name,
                            choice_name=choice_name,
                            ballot_order=order,
                            party=party,
                            votes=int(votes_raw.replace(',', '')),
                            vote_mode=mode,
                            source_id=source_id,
                            fetched_at=fetched_at,
                            raw_vote_mode=mode_raw,
                        )
                    )
    return observations
