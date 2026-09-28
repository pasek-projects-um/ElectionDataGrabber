from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class GeographyRelation(StrEnum):
    CONTAINS = "contains"
    ADMINISTERS = "administers"
    REPORTS_TO = "reports_to"
    OVERLAPS = "overlaps"
    SUPERSEDES = "supersedes"


@dataclass(frozen=True, slots=True)
class GeographyNode:
    geography_id: str
    state: str
    level: str
    canonical_name: str
    external_id_namespace: str = ""
    external_id: str = ""


@dataclass(frozen=True, slots=True)
class GeographyEdge:
    parent_id: str
    child_id: str
    relation: GeographyRelation
    effective_from: str = ""
    effective_to: str = ""
    additive: bool | None = None
    evidence_url: str = ""
    notes: str = ""

    def __post_init__(self) -> None:
        if self.parent_id == self.child_id:
            raise ValueError("geography relationship cannot self-reference")
        if self.relation in {GeographyRelation.CONTAINS, GeographyRelation.OVERLAPS} and self.additive is True:
            raise ValueError("geographic containment/overlap alone cannot imply arithmetic additivity")


def children(edges: list[GeographyEdge], parent_id: str, relation: GeographyRelation | None = None) -> list[str]:
    return [
        e.child_id for e in edges
        if e.parent_id == parent_id and (relation is None or e.relation == relation)
    ]


def validate_acyclic_reporting(edges: list[GeographyEdge]) -> None:
    graph: dict[str, list[str]] = {}
    for edge in edges:
        if edge.relation != GeographyRelation.REPORTS_TO:
            continue
        graph.setdefault(edge.child_id, []).append(edge.parent_id)
    visiting: set[str] = set()
    done: set[str] = set()

    def visit(node: str) -> None:
        if node in visiting:
            raise ValueError("reporting hierarchy contains a cycle")
        if node in done:
            return
        visiting.add(node)
        for nxt in graph.get(node, []):
            visit(nxt)
        visiting.remove(node)
        done.add(node)

    for node in list(graph):
        visit(node)
