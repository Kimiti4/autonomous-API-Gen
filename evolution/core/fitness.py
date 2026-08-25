"""Multi-objective fitness: typed dimensions, Pareto dominance, non-dominated sort, crowding distance."""

from __future__ import annotations

from enum import Enum
from typing import Mapping

from pydantic import BaseModel, ConfigDict, Field


class FitnessDimension(str, Enum):
    MODULARITY = "modularity"
    SIMPLICITY = "simplicity"
    TESTABILITY = "testability"
    SECURITY_POSTURE = "security_posture"
    DEPLOYABILITY = "deployability"


class FitnessVector(BaseModel):
    """Immutable mapping of FitnessDimension -> non-negative score."""

    model_config = ConfigDict(frozen=True)

    scores: Mapping[FitnessDimension, float] = Field(default_factory=dict)

    def as_dict(self) -> dict[str, float]:
        return {d.value: v for d, v in self.scores.items()}


def dominates(a: FitnessVector, b: FitnessVector) -> bool:
    """Return True iff a Pareto-dominates b (all dimensions >=, at least one >)."""
    a_vals = a.as_dict()
    b_vals = b.as_dict()
    all_dims = set(a_vals) | set(b_vals)
    at_least_one = False
    for d in all_dims:
        av = a_vals.get(d, 0.0)
        bv = b_vals.get(d, 0.0)
        if av < bv:
            return False
        if av > bv:
            at_least_one = True
    return at_least_one


def non_dominated_sort(vectors: list[FitnessVector]) -> list[list[int]]:
    """Return fronts as lists of indices into *vectors*."""
    n = len(vectors)
    if n == 0:
        return []
    domination_count = [0] * n
    dominated_sets: list[list[int]] = [[] for _ in range(n)]
    first_front: list[int] = []
    for i in range(n):
        for j in range(n):
            if i == j:
                continue
            if dominates(vectors[i], vectors[j]):
                dominated_sets[i].append(j)
            elif dominates(vectors[j], vectors[i]):
                domination_count[i] += 1
        if domination_count[i] == 0:
            first_front.append(i)
    if not first_front:
        return []
    fronts: list[list[int]] = [first_front]
    current = first_front
    while True:
        next_front: list[int] = []
        for i in current:
            for j in dominated_sets[i]:
                domination_count[j] -= 1
                if domination_count[j] == 0:
                    next_front.append(j)
        if not next_front:
            break
        fronts.append(next_front)
        current = next_front
    return fronts


def crowding_distance(
    front_indices: list[int], vectors: list[FitnessVector]
) -> dict[int, float]:
    """Compute crowding distance for one Pareto front."""
    if len(front_indices) <= 2:
        return {i: 1e9 for i in front_indices}
    distances: dict[int, float] = {i: 0.0 for i in front_indices}
    dims = list(FitnessDimension)
    for dim in dims:
        sorted_idx = sorted(
            front_indices, key=lambda i: vectors[i].scores.get(dim, 0.0)
        )
        distances[sorted_idx[0]] = 1e9
        distances[sorted_idx[-1]] = 1e9
        range_val = (
            vectors[sorted_idx[-1]].scores.get(dim, 0.0)
            - vectors[sorted_idx[0]].scores.get(dim, 0.0)
        )
        if range_val == 0:
            continue
        for k in range(1, len(sorted_idx) - 1):
            prev_val = vectors[sorted_idx[k - 1]].scores.get(dim, 0.0)
            next_val = vectors[sorted_idx[k + 1]].scores.get(dim, 0.0)
            distances[sorted_idx[k]] += (next_val - prev_val) / range_val
    return distances
