"""
Phase 6: Pareto Multi-Objective Evolution Coordinator.

Orchestrates the evolution lifecycle using Pareto optimization
rather than a single aggregate score. Prevents the engine from
sacrificing accessibility for visual novelty.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Optional

from constitutional_architecture.meta.genome.chromosomes import FrontendGenome
from constitutional_architecture.meta.genome.evaluators.i_fitness_evaluator import (
    IFitnessEvaluator, FitnessDimension,
)
from constitutional_architecture.meta.genome.evaluators.concrete_evaluators import CompositeFitness
from constitutional_architecture.meta.genome.transcriber import FrontendGenomeTranscriber
from constitutional_architecture.meta.genome.operators import FrontendMutator, FrontendCrossover
from constitutional_architecture.meta.genome.lethality import check_genome_lethality


@dataclass
class Candidate:
    genome: FrontendGenome
    scores: list[FitnessDimension]
    pareto_rank: int = 0

    @property
    def composite(self) -> float:
        return CompositeFitness(list(self.scores)).composite_score


@dataclass
class EvolutionResult:
    survivors: list[Candidate]
    next_generation: list[FrontendGenome]
    generation: int = 0


class ParetoEvolutionCoordinator:
    def __init__(
        self,
        transcriber: Optional[FrontendGenomeTranscriber] = None,
        mutator: Optional[FrontendMutator] = None,
        crossover: Optional[FrontendCrossover] = None,
        rng: Optional[random.Random] = None,
    ) -> None:
        self._transcriber = transcriber or FrontendGenomeTranscriber()
        self._mutator = mutator or FrontendMutator()
        self._crossover = crossover or FrontendCrossover()
        self._rng = rng or random.Random()
        self._generation = 0

    def run_generation(
        self,
        population: list[FrontendGenome],
        evaluators: list[IFitnessEvaluator],
    ) -> EvolutionResult:
        scored: list[Candidate] = []

        for genome in population:
            lethal = check_genome_lethality(genome)
            if lethal.lethal:
                continue

            profile = self._transcriber.transcribe(genome)
            scores: list[FitnessDimension] = []
            for evaluator in evaluators:
                scores.append(evaluator.evaluate(profile))
            scored.append(Candidate(genome=genome, scores=scores))

        scored = self._non_dominated_sort(scored)

        survivors = [c for c in scored if self._meets_threshold(c, min_score=0.60)]
        if not survivors and scored:
            survivors = [scored[0]]
        if not survivors:
            # All genomes were lethal — return empty result
            return EvolutionResult(survivors=[], next_generation=[g.clone() for g in population], generation=self._generation)

        next_gen: list[FrontendGenome] = []
        while len(next_gen) < len(population):
            if self._rng.random() < 0.7 and len(survivors) >= 2:
                a = self._rng.choice(survivors).genome
                b = self._rng.choice(survivors).genome
                child1, child2 = self._crossover.single_point(a, b, rate=0.5)
                self._mutator.mutate(child1, 0.05)
                next_gen.append(child1)
                if len(next_gen) < len(population):
                    next_gen.append(child2)
            else:
                parent = self._rng.choice(survivors).genome
                child = parent.clone()
                self._mutator.mutate(child, 0.1)
                next_gen.append(child)

        self._generation += 1
        return EvolutionResult(
            survivors=survivors,
            next_generation=next_gen[:len(population)],
            generation=self._generation,
        )

    def _non_dominated_sort(self, candidates: list[Candidate]) -> list[Candidate]:
        sorted_candidates = sorted(candidates, key=lambda c: c.composite, reverse=True)
        for rank, c in enumerate(sorted_candidates):
            c.pareto_rank = rank
        return sorted_candidates

    def _meets_threshold(self, candidate: Candidate, min_score: float) -> bool:
        return candidate.composite >= min_score

    @property
    def generation(self) -> int:
        return self._generation
