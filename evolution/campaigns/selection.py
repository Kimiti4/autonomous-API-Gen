"""
Pareto selection for multi-objective evolutionary campaigns.
"""

from __future__ import annotations

from typing import Dict, List

from .models import CandidateFitness


def dominates(
    left: Dict[str, float],
    right: Dict[str, float],
) -> bool:
    """
    Return true when left dominates right.

    Left dominates right when left is greater than or equal to right in all
    objectives and strictly greater in at least one objective.
    """

    at_least_one_better = False

    all_objectives = set(left.keys()).union(right.keys())

    for objective in all_objectives:
        left_value = float(left.get(objective, 0.0))
        right_value = float(right.get(objective, 0.0))

        if left_value < right_value:
            return False

        if left_value > right_value:
            at_least_one_better = True

    return at_least_one_better


def select_pareto_front(
    fitness_results: Dict[str, CandidateFitness],
) -> List[str]:
    """
    Return the first Pareto front from candidate fitness results.

    Candidates failing constraints are excluded.
    """

    valid_candidates = {
        candidate_id: fitness
        for candidate_id, fitness in fitness_results.items()
        if fitness.passed
        and all(fitness.constraints.values())
    }

    if not valid_candidates:
        return []

    non_dominated: List[str] = []

    for candidate_id, fitness in valid_candidates.items():
        dominated = False

        for other_id, other_fitness in valid_candidates.items():
            if candidate_id == other_id:
                continue

            if dominates(other_fitness.objectives, fitness.objectives):
                dominated = True
                break

        if not dominated:
            non_dominated.append(candidate_id)

    return sorted(non_dominated)
