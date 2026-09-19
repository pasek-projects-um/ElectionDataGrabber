from __future__ import annotations

import re
from dataclasses import dataclass
from enum import StrEnum

from election_data_grabber.models import VoteMode


class VoteModeMappingStatus(StrEnum):
    VERIFIED = "verified"
    CANDIDATE = "candidate"
    REJECTED = "rejected"


class VoteModeAggregation(StrEnum):
    COMPONENT = "component"
    AGGREGATE = "aggregate"
    UNKNOWN = "unknown"


@dataclass(frozen=True, slots=True)
class VoteModeRule:
    raw_label: str
    vote_mode: VoteMode
    mapping_method: str
    evidence_reference: str
    status: VoteModeMappingStatus = VoteModeMappingStatus.VERIFIED
    state: str | None = None
    source_id: str | None = None
    aggregation: VoteModeAggregation = VoteModeAggregation.COMPONENT

    def __post_init__(self) -> None:
        if not self.raw_label.strip() or not self.mapping_method.strip() or not self.evidence_reference.strip():
            raise ValueError("vote-mode rule requires raw label, method, and evidence")
        if self.state is not None and not re.fullmatch(r"[A-Z]{2}", self.state.strip().upper()):
            raise ValueError("invalid vote-mode rule state")


@dataclass(frozen=True, slots=True)
class VoteModeResolution:
    raw_label: str
    vote_mode: VoteMode | None
    rule: VoteModeRule | None

    @property
    def recognized(self) -> bool:
        return self.rule is not None and self.vote_mode is not None


def _label(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", value.strip().lower()).strip()


def validate_vote_mode_rules(rows: list[VoteModeRule]) -> None:
    seen: dict[tuple[str, str | None, str | None], VoteModeRule] = {}
    for row in rows:
        key = (_label(row.raw_label), row.state.upper() if row.state else None, row.source_id)
        prior = seen.get(key)
        if prior:
            prior_semantics = (
                prior.vote_mode, prior.mapping_method, prior.evidence_reference,
                prior.status, prior.aggregation,
            )
            row_semantics = (
                row.vote_mode, row.mapping_method, row.evidence_reference,
                row.status, row.aggregation,
            )
            if prior_semantics != row_semantics:
                raise ValueError(f"conflicting vote-mode rule: {key}")
        else:
            seen[key] = row


def resolve_vote_mode(raw_label: str, rules: list[VoteModeRule], *, state: str | None = None, source_id: str | None = None) -> VoteModeResolution:
    validate_vote_mode_rules(rules)
    normalized = _label(raw_label)
    candidates = [
        row for row in rules
        if row.status == VoteModeMappingStatus.VERIFIED
        and _label(row.raw_label) == normalized
        and (row.state is None or (state and row.state.upper() == state.upper()))
        and (row.source_id is None or row.source_id == source_id)
    ]
    if not candidates:
        return VoteModeResolution(raw_label, None, None)

    def specificity(row: VoteModeRule) -> tuple[int, int]:
        # State and source are independent scoping dimensions. A rule scoped to
        # both outranks either alone; state-only and source-only are peers and
        # conflicting peer rules must remain unresolved rather than relying on
        # an arbitrary dimension precedence.
        scoped = int(row.source_id is not None) + int(row.state is not None)
        return (scoped, 0)

    candidates.sort(key=specificity, reverse=True)
    best = specificity(candidates[0])
    tied = [row for row in candidates if specificity(row) == best]
    modes = {(row.vote_mode, row.aggregation) for row in tied}
    if len(modes) != 1:
        return VoteModeResolution(raw_label, None, None)
    return VoteModeResolution(raw_label, tied[0].vote_mode, tied[0])


DEFAULT_RULES = [
    VoteModeRule("election day", VoteMode.ELECTION_DAY, "literal_label", "governed_default", aggregation=VoteModeAggregation.COMPONENT),
    VoteModeRule("election_day", VoteMode.ELECTION_DAY, "literal_label", "governed_default", aggregation=VoteModeAggregation.COMPONENT),
    VoteModeRule("electionday", VoteMode.ELECTION_DAY, "literal_label", "governed_default", aggregation=VoteModeAggregation.COMPONENT),
    VoteModeRule("ed", VoteMode.ELECTION_DAY, "literal_label", "governed_default", aggregation=VoteModeAggregation.COMPONENT),
    VoteModeRule("early", VoteMode.EARLY, "literal_label", "governed_default", aggregation=VoteModeAggregation.COMPONENT),
    VoteModeRule("early voting", VoteMode.EARLY, "literal_label", "governed_default", aggregation=VoteModeAggregation.COMPONENT),
    VoteModeRule("early_voting", VoteMode.EARLY, "literal_label", "governed_default", aggregation=VoteModeAggregation.COMPONENT),
    VoteModeRule("earlyvoting", VoteMode.EARLY, "literal_label", "governed_default", aggregation=VoteModeAggregation.COMPONENT),
    VoteModeRule("absentee", VoteMode.ABSENTEE, "literal_label", "governed_default", aggregation=VoteModeAggregation.COMPONENT),
    VoteModeRule("mail", VoteMode.MAIL, "literal_label", "governed_default", aggregation=VoteModeAggregation.COMPONENT),
    VoteModeRule("provisional", VoteMode.PROVISIONAL, "literal_label", "governed_default", aggregation=VoteModeAggregation.COMPONENT),
    VoteModeRule("uocava", VoteMode.UOCAVA, "literal_label", "governed_default", aggregation=VoteModeAggregation.COMPONENT),
    VoteModeRule("total", VoteMode.TOTAL, "literal_label", "governed_default", aggregation=VoteModeAggregation.AGGREGATE),
    VoteModeRule("total votes", VoteMode.TOTAL, "literal_label", "governed_default", aggregation=VoteModeAggregation.AGGREGATE),
    VoteModeRule("votes", VoteMode.TOTAL, "literal_label", "governed_default", aggregation=VoteModeAggregation.AGGREGATE),
    VoteModeRule("votecount", VoteMode.TOTAL, "literal_label", "governed_default", aggregation=VoteModeAggregation.AGGREGATE),
    VoteModeRule("av", VoteMode.ABSENTEE, "state_semantic_override", "mi_av_semantics", state="MI"),
    VoteModeRule("av counting boards", VoteMode.ABSENTEE, "state_semantic_override", "mi_av_semantics", state="MI"),
    VoteModeRule("av_counting_boards", VoteMode.ABSENTEE, "state_semantic_override", "mi_av_semantics", state="MI"),
    VoteModeRule("pre process absentee", VoteMode.ABSENTEE, "state_semantic_override", "mi_av_semantics", state="MI"),
    VoteModeRule("pre_process_absentee", VoteMode.ABSENTEE, "state_semantic_override", "mi_av_semantics", state="MI"),
]


def normalize_vote_mode(raw_label: str, *, state: str | None = None, source_id: str | None = None, rules: list[VoteModeRule] | None = None) -> VoteModeResolution:
    return resolve_vote_mode(raw_label, rules or DEFAULT_RULES, state=state, source_id=source_id)


def assert_no_aggregate_component_double_count(rows: list[object]) -> None:
    """Reject a result set that would sum TOTAL alongside mode components."""
    groups: dict[tuple, set[VoteMode]] = {}
    for row in rows:
        key = (
            getattr(row, "election_id", None), getattr(row, "jurisdiction_id", None),
            getattr(row, "source_id", None), getattr(row, "snapshot_sha256", None) or getattr(row, "fetched_at", None),
            getattr(row, "reporting_unit_id", None), getattr(row, "contest_id", None) or getattr(row, "contest_name", None),
            getattr(row, "choice_id", None) or getattr(row, "choice_name", None),
        )
        groups.setdefault(key, set()).add(getattr(row, "vote_mode"))
    for key, modes in groups.items():
        additive_components = modes - {VoteMode.TOTAL, VoteMode.UNKNOWN, VoteMode.OTHER}
        if VoteMode.TOTAL in modes and additive_components:
            raise ValueError(f"aggregate total and component vote modes coexist; choose one aggregation basis: {key}")
