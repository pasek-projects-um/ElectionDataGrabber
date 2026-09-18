from __future__ import annotations

import csv
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path


class CoverageStatus(StrEnum):
    ENUMERATED_UNRESOLVED = "enumerated_unresolved"
    FINAL_ONLY = "final_only"
    ELECTION_NIGHT_ONLY = "election_night_only"
    BOTH = "both"
    KNOWN_MISSING_SOURCE = "known_missing_source"


class EstimateStatus(StrEnum):
    AUTHORITATIVE = "authoritative"
    HIGH_CONFIDENCE = "high_confidence"
    PROVISIONAL = "provisional"


@dataclass(frozen=True, slots=True)
class PrimaryElectionLocality:
    jurisdiction_id: str
    state: str
    jurisdiction_level: str
    canonical_name: str
    id_status: str
    coverage_status: CoverageStatus
    authority_id: str = ""
    external_id_namespace: str = ""
    external_id: str = ""
    final_capable: bool = False
    election_night_capable: bool = False
    final_evidence_url: str = ""
    election_night_evidence_url: str = ""
    final_source_id: str = ""
    election_night_source_id: str = ""
    assessment_method: str = ""
    assessment_status: str = ""
    first_verified_at: str = ""
    last_verified_at: str = ""
    notes: str = ""

    def __post_init__(self) -> None:
        if not self.jurisdiction_id.startswith("us:"):
            raise ValueError("locality requires canonical jurisdiction_id")
        if self.authority_id and not self.authority_id.startswith("us:authority:"):
            raise ValueError("authority_id must use independent authority namespace")
        expected = {
            CoverageStatus.ENUMERATED_UNRESOLVED: (False, False),
            CoverageStatus.FINAL_ONLY: (True, False),
            CoverageStatus.ELECTION_NIGHT_ONLY: (False, True),
            CoverageStatus.BOTH: (True, True),
        }
        if self.coverage_status in expected and expected[self.coverage_status] != (self.final_capable, self.election_night_capable):
            raise ValueError("coverage_status disagrees with capability flags")
        if self.coverage_status == CoverageStatus.KNOWN_MISSING_SOURCE:
            if self.final_capable or self.election_night_capable:
                raise ValueError("known_missing_source cannot be capability-positive")
            if self.assessment_status != "affirmatively_adjudicated" or not self.assessment_method:
                raise ValueError("known_missing_source requires affirmative adjudication")


@dataclass(frozen=True, slots=True)
class LocalityDenominator:
    state: str
    expected_primary_units: int
    authority_model: str
    estimate_status: EstimateStatus
    evidence_method: str
    evidence_url: str = ""
    effective_from: str = ""
    effective_to: str = ""
    notes: str = ""

    def __post_init__(self) -> None:
        if len(self.state) != 2 or self.expected_primary_units < 0:
            raise ValueError("invalid denominator")
        if not self.evidence_method:
            raise ValueError("denominator requires provenance method")


def derive_tracker(\n    localities: list[PrimaryElectionLocality],\n    denominators: list[LocalityDenominator],\n    capability_map: dict[str, tuple[bool, bool]] | None = None,\n) -> list[dict[str, str]]:\n    """Derive coverage counts.\n\n    When capability_map is supplied it is authoritative for positive source\n    capability. Stored locality capability fields are then compatibility data\n    only. KNOWN_MISSING_SOURCE remains an explicit affirmative adjudication;\n    absence of a positive source record never implies missing-source status.\n    """\n    by_state: dict[str, dict[CoverageStatus, int]] = {}
    seen: set[str] = set()
    for row in localities:
        if row.jurisdiction_id in seen:
            raise ValueError(f"duplicate locality: {row.jurisdiction_id}")
        seen.add(row.jurisdiction_id)
        counts = by_state.setdefault(row.state, {s: 0 for s in CoverageStatus})\n        status = row.coverage_status\n        if capability_map is not None:\n            final, live = capability_map.get(row.jurisdiction_id, (False, False))\n            if final and live:\n                status = CoverageStatus.BOTH\n            elif final:\n                status = CoverageStatus.FINAL_ONLY\n            elif live:\n                status = CoverageStatus.ELECTION_NIGHT_ONLY\n            elif row.coverage_status == CoverageStatus.KNOWN_MISSING_SOURCE:\n                status = CoverageStatus.KNOWN_MISSING_SOURCE\n            else:\n                status = CoverageStatus.ENUMERATED_UNRESOLVED\n        counts[status] += 1

    out = []
    national_expected = national_enumerated = 0
    for d in sorted(denominators, key=lambda x: x.state):
        counts = by_state.get(d.state, {s: 0 for s in CoverageStatus})
        enumerated = sum(counts.values())
        if enumerated > d.expected_primary_units:
            raise ValueError(f"{d.state}: enumerated localities exceed denominator")
        unknown = d.expected_primary_units - enumerated
        national_expected += d.expected_primary_units
        national_enumerated += enumerated
        out.append({
            "state": d.state,
            "expected_primary_units": str(d.expected_primary_units),
            "enumerated_unresolved": str(counts[CoverageStatus.ENUMERATED_UNRESOLVED]),
            "known_final_only": str(counts[CoverageStatus.FINAL_ONLY]),
            "known_election_night_only": str(counts[CoverageStatus.ELECTION_NIGHT_ONLY]),
            "known_both": str(counts[CoverageStatus.BOTH]),
            "known_units_missing_source": str(counts[CoverageStatus.KNOWN_MISSING_SOURCE]),
            "estimated_unknown_units": str(unknown),
            "known_units_with_any_source": str(counts[CoverageStatus.FINAL_ONLY] + counts[CoverageStatus.ELECTION_NIGHT_ONLY] + counts[CoverageStatus.BOTH]),
            "known_units_with_final": str(counts[CoverageStatus.FINAL_ONLY] + counts[CoverageStatus.BOTH]),
            "known_units_with_election_night": str(counts[CoverageStatus.ELECTION_NIGHT_ONLY] + counts[CoverageStatus.BOTH]),
            "authority_model": d.authority_model,
            "estimate_status": d.estimate_status.value,
            "evidence_method": d.evidence_method,
        })
    if sum(int(r["expected_primary_units"]) for r in out) != national_expected:
        raise AssertionError("national denominator mismatch")
    if sum(int(r["expected_primary_units"]) - int(r["estimated_unknown_units"]) for r in out) != national_enumerated:
        raise AssertionError("national enumeration mismatch")
    return out


def read_localities(path: Path) -> list[PrimaryElectionLocality]:
    with path.open(encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    def yes(v: str) -> bool: return v.strip().lower() in {"1", "true", "yes"}
    return [PrimaryElectionLocality(
        jurisdiction_id=r["jurisdiction_id"], state=r["state"], jurisdiction_level=r["jurisdiction_level"],
        canonical_name=r["canonical_name"], id_status=r["id_status"], coverage_status=CoverageStatus(r["coverage_status"]),
        authority_id=r.get("authority_id",""), external_id_namespace=r.get("external_id_namespace",""),
        external_id=r.get("external_id",""), final_capable=yes(r.get("final_capable","")),
        election_night_capable=yes(r.get("election_night_capable","")), final_evidence_url=r.get("final_evidence_url",""),
        election_night_evidence_url=r.get("election_night_evidence_url",""), final_source_id=r.get("final_source_id",""),
        election_night_source_id=r.get("election_night_source_id",""), assessment_method=r.get("assessment_method",""),
        assessment_status=r.get("assessment_status",""), first_verified_at=r.get("first_verified_at",""),
        last_verified_at=r.get("last_verified_at",""), notes=r.get("notes","")) for r in rows]


def read_denominators(path: Path) -> list[LocalityDenominator]:
    with path.open(encoding="utf-8-sig", newline="") as f:
        return [LocalityDenominator(
            state=r["state"], expected_primary_units=int(r["expected_primary_units"]), authority_model=r["authority_model"],
            estimate_status=EstimateStatus(r["estimate_status"]), evidence_method=r["evidence_method"],
            evidence_url=r.get("evidence_url",""), effective_from=r.get("effective_from",""),
            effective_to=r.get("effective_to",""), notes=r.get("notes","")) for r in csv.DictReader(f)]
