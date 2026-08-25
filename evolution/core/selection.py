"""Pareto selection: non-dominated sort + crowding distance."""

from __future__ import annotations

from evolution.core.fitness import (
    FitnessVector,
    crowding_distance,
    non_dominated_sort,
)


class ReferenceParetoSelection:
    """Select non-dominated genome with best crowding distance."""

    def select(self, candidates: list[FitnessVector]) -> int:
        if not candidates:
            raise ValueError("No candidates to select from")
        fronts = non_dominated_sort(candidates)
        if not fronts:
            return 0
        first = fronts[0]
        if len(first) == 1:
            return first[0]
        dists = crowding_distance(first, candidates)
        return max(first, key=lambda i: dists[i])
