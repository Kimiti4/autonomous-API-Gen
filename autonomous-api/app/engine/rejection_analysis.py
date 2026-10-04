"""Record rejected ESAP candidates and compute evidence-backed counterfactuals."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Sequence

from .pareto_architecture import ArchitectureScore, Objective, build_frontier


@dataclass(frozen=True)
class RejectionRecord:
    candidate_architecture_id: str
    status: str
    reasons: tuple[str, ...]
    score: ArchitectureScore
    frontier: tuple[str, ...]
    evidence: tuple[str, ...]


@dataclass(frozen=True)
class CounterfactualRequirement:
    candidate_architecture_id: str
    objective: str
    direction: str
    current_value: float
    required_value: float
    delta: float
    evidence: tuple[str, ...]


def record_rejection(
    candidate: ArchitectureScore,
    *,
    reasons: Sequence[str],
    frontier_scores: Sequence[ArchitectureScore],
    objectives: Sequence[Objective],
) -> RejectionRecord:
    if not candidate.evidence:
        raise ValueError("rejection-score-requires-evidence")
    frontier = build_frontier(tuple(frontier_scores) + (candidate,), objectives)
    normalized = tuple(sorted(set(str(reason) for reason in reasons if reason)))
    if not normalized:
        raise ValueError("rejection-requires-reason")
    return RejectionRecord(
        candidate.architecture_id,
        "rejected",
        normalized,
        candidate,
        frontier.frontier,
        tuple(sorted(set(candidate.evidence))),
    )


def derive_counterfactual_requirements(
    rejection: RejectionRecord,
    frontier_scores: Sequence[ArchitectureScore],
    objectives: Sequence[Objective],
) -> tuple[CounterfactualRequirement, ...]:
    """Return minimum per-objective changes needed to stop each frontier member dominating.

    These are necessary thresholds, not claims that changing one metric alone
    guarantees admission.
    """
    candidate = rejection.score
    requirements: list[CounterfactualRequirement] = []

    for dominator in frontier_scores:
        if dominator.architecture_id == candidate.architecture_id:
            continue
        if not _dominates(dominator, candidate, objectives):
            continue

        for objective in objectives:
            a = candidate.values[objective.name]
            b = dominator.values[objective.name]
            if objective.direction == "maximize" and a <= b:
                required = b
                delta = required - a
            elif objective.direction == "minimize" and a >= b:
                required = b
                delta = a - required
            else:
                continue
            requirements.append(
                CounterfactualRequirement(
                    candidate.architecture_id,
                    objective.name,
                    objective.direction,
                    float(a),
                    float(required),
                    float(delta),
                    tuple(sorted(set(candidate.evidence))),
                )
            )

    unique: dict[tuple[str, str, float, float], CounterfactualRequirement] = {}
    for requirement in requirements:
        key = (
            requirement.candidate_architecture_id,
            requirement.objective,
            requirement.current_value,
            requirement.required_value,
        )
        unique[key] = requirement
    return tuple(unique.values())


def _dominates(
    left: ArchitectureScore,
    right: ArchitectureScore,
    objectives: Sequence[Objective],
) -> bool:
    return any(
        score.architecture_id == right.architecture_id
        for score in build_frontier((left, right), objectives).dominated
    )
