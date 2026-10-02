"""Constraint-driven engineering exploration.

Generates *candidate spaces*, not a fixed architecture or ranking. The caller/
Evolution Engine supplies domain-specific candidates and evidence. This keeps
Tiannara free to invent designs while making senior engineering concerns
explicit and testable.
"""
from __future__ import annotations
from dataclasses import dataclass
from .engineering_quality import EngineeringDiscipline, quality_profile


@dataclass(frozen=True)
class EngineeringDesign:
    design_id: str
    description: str
    assumptions: tuple[str, ...] = ()
    risks: tuple[str, ...] = ()
    quality_obligations: tuple[str, ...] = ()


@dataclass(frozen=True)
class ExplorationResult:
    discipline: EngineeringDiscipline
    candidates: tuple[EngineeringDesign, ...]
    required_obligations: tuple[str, ...]
    unresolved: tuple[str, ...] = ()


def prepare_exploration(
    discipline: EngineeringDiscipline,
    candidates: tuple[EngineeringDesign, ...],
) -> ExplorationResult:
    profile = quality_profile(discipline)
    required = tuple(o.obligation_id for o in profile.obligations)
    unresolved = []
    if len(candidates) < 2:
        unresolved.append("insufficient design diversity: provide at least two viable candidates")
    for candidate in candidates:
        if not candidate.assumptions:
            unresolved.append(f"{candidate.design_id}: assumptions not declared")
        if not candidate.risks:
            unresolved.append(f"{candidate.design_id}: risks not declared")
    return ExplorationResult(discipline, candidates, required, tuple(unresolved))


def candidate_gaps(result: ExplorationResult) -> dict[str, tuple[str, ...]]:
    required = set(result.required_obligations)
    return {
        c.design_id: tuple(sorted(required - set(c.quality_obligations)))
        for c in result.candidates
    }
