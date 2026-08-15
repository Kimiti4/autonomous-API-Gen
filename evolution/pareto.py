"""
Pareto selection for multi-candidate evolution.

This module implements:
- Pareto dominance
- fast non-dominated sorting
- crowding distance ranking
- multi-objective candidate selection

It intentionally avoids collapsing architectures into a single aggregate score.
"""

from __future__ import annotations

from typing import Dict, List

from .models import (
    CandidateEvaluationRecord,
    ParetoCandidate,
    ParetoSelectionPolicy,
    ParetoSelectionResult,
    utcnow,
)


LARGE_CROWDING_DISTANCE = 1_000_000_000.0


def dominates(
    a: Dict[str, float],
    b: Dict[str, float],
    objectives: List[str],
    epsilon: float = 0.0,
) -> bool:
    """
    Return true if candidate `a` dominates candidate `b`.

    All objectives are treated as objectives to maximize.

    Candidate `a` dominates candidate `b` when:
    - `a` is at least as good as `b` in all objectives
    - `a` is strictly better than `b` in at least one objective
    """

    at_least_one_better = False

    for objective in objectives:
        a_value = float(a.get(objective, 0.0))
        b_value = float(b.get(objective, 0.0))

        if a_value + epsilon < b_value:
            return False

        if a_value > b_value + epsilon:
            at_least_one_better = True

    return at_least_one_better


def non_dominated_sort(
    values_by_candidate: Dict[str, Dict[str, float]],
    objectives: List[str],
    epsilon: float = 0.0,
) -> List[List[str]]:
    """
    Perform fast non-dominated sorting.

    Returns a list of fronts.

    Each front is a list of candidate IDs.
    """

    candidate_ids = list(values_by_candidate.keys())

    if not candidate_ids:
        return []

    domination_count: Dict[str, int] = {
        candidate_id: 0
        for candidate_id in candidate_ids
    }

    dominated_sets: Dict[str, List[str]] = {
        candidate_id: []
        for candidate_id in candidate_ids
    }

    first_front: List[str] = []

    for candidate_id in candidate_ids:
        for other_id in candidate_ids:
            if candidate_id == other_id:
                continue

            if dominates(
                values_by_candidate[candidate_id],
                values_by_candidate[other_id],
                objectives,
                epsilon,
            ):
                dominated_sets[candidate_id].append(other_id)

            elif dominates(
                values_by_candidate[other_id],
                values_by_candidate[candidate_id],
                objectives,
                epsilon,
            ):
                domination_count[candidate_id] += 1

        if domination_count[candidate_id] == 0:
            first_front.append(candidate_id)

    if not first_front:
        return []

    fronts: List[List[str]] = [first_front]
    current_front = first_front

    while True:
        next_front: List[str] = []

        for candidate_id in current_front:
            for dominated_id in dominated_sets[candidate_id]:
                domination_count[dominated_id] -= 1

                if domination_count[dominated_id] == 0:
                    next_front.append(dominated_id)

        if not next_front:
            break

        fronts.append(next_front)
        current_front = next_front

    return fronts


def crowding_distance(
    front_candidate_ids: List[str],
    objectives: List[str],
    values_by_candidate: Dict[str, Dict[str, float]],
) -> Dict[str, float]:
    """
    Compute crowding distance for a Pareto front.

    Crowding distance preserves diversity within a front.
    """

    if not front_candidate_ids:
        return {}

    if len(front_candidate_ids) <= 2:
        return {
            candidate_id: LARGE_CROWDING_DISTANCE
            for candidate_id in front_candidate_ids
        }

    distances: Dict[str, float] = {
        candidate_id: 0.0
        for candidate_id in front_candidate_ids
    }

    for objective in objectives:
        sorted_ids = sorted(
            front_candidate_ids,
            key=lambda candidate_id: float(
                values_by_candidate[candidate_id].get(objective, 0.0)
            ),
        )

        min_value = float(values_by_candidate[sorted_ids[0]].get(objective, 0.0))
        max_value = float(values_by_candidate[sorted_ids[-1]].get(objective, 0.0))

        distances[sorted_ids[0]] = LARGE_CROWDING_DISTANCE
        distances[sorted_ids[-1]] = LARGE_CROWDING_DISTANCE

        if max_value == min_value:
            continue

        range_value = max_value - min_value

        for index in range(1, len(sorted_ids) - 1):
            previous_id = sorted_ids[index - 1]
            next_id = sorted_ids[index + 1]

            previous_value = float(
                values_by_candidate[previous_id].get(objective, 0.0)
            )

            next_value = float(
                values_by_candidate[next_id].get(objective, 0.0)
            )

            distances[sorted_ids[index]] += (
                next_value - previous_value
            ) / range_value

    return distances


def select_pareto(
    proposal_id: str,
    evaluations: List[CandidateEvaluationRecord],
    policy: ParetoSelectionPolicy,
) -> ParetoSelectionResult:
    """
    Select preferred candidates using Pareto ranking.
    """

    feasible_evaluations: List[CandidateEvaluationRecord] = []

    for evaluation in evaluations:
        if not evaluation.fitness:
            continue

        if not evaluation.feasible:
            continue

        if policy.require_constraints:
            constraints = evaluation.fitness.constraints

            if not all(constraints.values()):
                continue

        objective_values = evaluation.fitness.objectives

        below_threshold = any(
            float(value) < policy.min_objective_value
            for value in objective_values.values()
        )

        if below_threshold:
            continue

        feasible_evaluations.append(evaluation)

    created_at = utcnow().isoformat()

    if not feasible_evaluations:
        return ParetoSelectionResult(
            proposal_id=proposal_id,
            objectives=policy.objectives,
            fronts=[],
            selected_candidate_ids=[],
            selected_candidate_id=None,
            created_at=created_at,
        )

    if policy.objectives:
        objectives = list(policy.objectives)
    else:
        objective_names: set[str] = set()

        for evaluation in feasible_evaluations:
            objective_names.update(evaluation.fitness.objectives.keys())

        objectives = sorted(objective_names)

    values_by_candidate: Dict[str, Dict[str, float]] = {}

    for evaluation in feasible_evaluations:
        values_by_candidate[evaluation.candidate_id] = {
            objective: float(
                evaluation.fitness.objectives.get(objective, 0.0)
            )
            for objective in objectives
        }

    fronts = non_dominated_sort(
        values_by_candidate=values_by_candidate,
        objectives=objectives,
        epsilon=policy.epsilon,
    )

    front_models: List[List[ParetoCandidate]] = []
    selected_candidate_ids: List[str] = []

    for rank, front_ids in enumerate(fronts):
        distances = crowding_distance(
            front_candidate_ids=front_ids,
            objectives=objectives,
            values_by_candidate=values_by_candidate,
        )

        sorted_front = sorted(
            front_ids,
            key=lambda candidate_id: (
                -distances[candidate_id],
                tuple(
                    -float(values_by_candidate[candidate_id].get(objective, 0.0))
                    for objective in objectives
                ),
                candidate_id,
            ),
        )

        front_models.append(
            [
                ParetoCandidate(
                    candidate_id=candidate_id,
                    rank=rank,
                    crowding_distance=distances[candidate_id],
                    objectives=values_by_candidate[candidate_id],
                )
                for candidate_id in sorted_front
            ]
        )

        for candidate_id in sorted_front:
            if len(selected_candidate_ids) < policy.max_selected:
                selected_candidate_ids.append(candidate_id)

        if len(selected_candidate_ids) >= policy.max_selected:
            break

    selected_candidate_id = (
        selected_candidate_ids[0]
        if selected_candidate_ids
        else None
    )

    return ParetoSelectionResult(
        proposal_id=proposal_id,
        objectives=objectives,
        fronts=front_models,
        selected_candidate_ids=selected_candidate_ids,
        selected_candidate_id=selected_candidate_id,
        created_at=created_at,
    )
