"""R2.9.3 -- Diversity observation (measure, do not optimize).

Computes population-diversity metrics for the anti-monoculture work in R2.9.4.
In R2.9.3 this is observe-only: the metrics are recorded in ``EvolutionState``
but never influence Pareto or selection. Collapsing to entropy 0 is a
diagnosis, not yet a selection signal -- R2.9.4 decides whether to act, and
only with evidence.
"""
from __future__ import annotations

import math
from collections import Counter
from typing import Mapping, Sequence

from tiannara.application.evolution.evolution_state import DiversityMetrics
from tiannara.application.evolution.ledger import stable_isr_hash

_DELTA_CANONICAL_KEYS = ("entries",)


class DiversityObserver:
    """Observe-only diversity metrics over a generated population and its
    scored evaluations. Operates on the pre-deduplication population so
    ``duplicate_rate`` is informative."""

    def observe(self, candidates: Sequence, scored: Sequence) -> DiversityMetrics:
        population_size = len(candidates)
        if population_size == 0:
            return DiversityMetrics(
                population_size=0, unique_isr_count=0, unique_delta_count=0,
                mutation_operator_distribution={}, genotype_entropy=0.0,
                phenotype_diversity=0.0, duplicate_rate=0.0,
            )

        unique_isrs = {stable_isr_hash(c.candidate_isr) for c in candidates}
        unique_deltas = {self._delta_canonical_hash(c) for c in candidates}
        op_dist = dict(Counter(c.operator_id for c in candidates))

        return DiversityMetrics(
            population_size=population_size,
            unique_isr_count=len(unique_isrs),
            unique_delta_count=len(unique_deltas),
            mutation_operator_distribution=op_dist,
            genotype_entropy=self._shannon_entropy(op_dist),
            phenotype_diversity=self._phenotype_diversity(scored),
            duplicate_rate=1.0 - (len(unique_isrs) / population_size),
        )

    @staticmethod
    def _delta_canonical_hash(candidate) -> str:
        from tiannara.domain.services.canonical import canonical_hash

        entries = candidate.mutation_delta.entries
        return canonical_hash({_DELTA_CANONICAL_KEYS[0]: list(entries)})

    @staticmethod
    def _shannon_entropy(distribution: Mapping[str, int]) -> float:
        total = sum(distribution.values())
        if total == 0:
            return 0.0
        entropy = 0.0
        for count in distribution.values():
            p = count / total
            if p > 0:
                entropy -= p * math.log2(p)
        return round(entropy, 6)

    @staticmethod
    def _phenotype_diversity(scored: Sequence) -> float:
        """Fraction of evaluated candidates with a distinct fitness signature."""
        if not scored:
            return 0.0
        signatures = {
            tuple(round(v, 4) for _, v in s.fitness.objectives)
            for s in scored
        }
        return round(len(signatures) / len(scored), 6)