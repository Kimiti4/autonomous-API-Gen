"""Unified requirement-to-architecture planning bridge for ESAP Bucket 3.

This creates traceable obligations without inventing implementation details.
Every proposed architecture obligation points back to a requirement and must
be verified before it can participate in governed evolution.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Mapping, Any
from .requirement_ir import RequirementGraph, RequirementKind
from .architecture_obligations import ArchitectureObligation


@dataclass(frozen=True)
class RequirementArchitectureLink:
    requirement_id: str
    obligation_id: str
    rationale: str


@dataclass(frozen=True)
class ArchitecturePlan:
    links: tuple[RequirementArchitectureLink, ...]
    unresolved_requirement_ids: tuple[str, ...]


def derive_architecture_plan(
    graph: RequirementGraph,
    obligations_by_requirement: Mapping[str, tuple[ArchitectureObligation, ...]],
) -> ArchitecturePlan:
    if graph.issues:
        return ArchitecturePlan((), tuple(sorted(r.requirement_id for r in graph.requirements)))
    links=[]
    unresolved=[]
    for req in graph.requirements:
        obligations=obligations_by_requirement.get(req.requirement_id, ())
        if not obligations:
            unresolved.append(req.requirement_id)
            continue
        for obligation in obligations:
            links.append(RequirementArchitectureLink(
                req.requirement_id,
                obligation.obligation_id,
                f"Architecture obligation {obligation.obligation_id} satisfies requirement {req.requirement_id}.",
            ))
    return ArchitecturePlan(tuple(links), tuple(sorted(unresolved)))
