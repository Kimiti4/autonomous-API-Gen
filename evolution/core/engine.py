"""EvolutionEngine: full constructive pipeline composing all ADR-011 stages."""

from __future__ import annotations

from typing import Protocol

from evolution.core.construction import ReferenceGenomeConstructor
from evolution.core.fitness import FitnessVector
from evolution.core.fitness_evaluator import ReferenceISRFitnessEvaluator
from evolution.core.genome import DecisionSpace, Genome, genome_content_hash
from evolution.core.materialize import ReferenceGenomeMaterializer
from evolution.core.operations import (
    CrossoverOperator,
    MutationOperator,
    OperationRecord,
    ReferenceCrossoverOperator,
    ReferenceMutationOperator,
)
from evolution.core.refinement import ReferenceArchitectureRefinement
from evolution.core.selection import ReferenceParetoSelection
from isr.core.graph import ISRGraph
from isr.core.revision import ISRRevision


class EvolutionObserver(Protocol):
    def on_event(self, event: dict) -> None: ...


class NullObserver:
    def on_event(self, event: dict) -> None:
        pass


class EvolutionEngine:
    """Compose all stages: construct -> evaluate -> mutate -> crossover
    -> select -> materialize -> refine -> produce ISR candidate."""

    def __init__(
        self,
        *,
        constructor: ReferenceGenomeConstructor | None = None,
        evaluator: ReferenceISRFitnessEvaluator | None = None,
        mutation_op: MutationOperator | None = None,
        crossover_op: CrossoverOperator | None = None,
        selector: ReferenceParetoSelection | None = None,
        materializer: ReferenceGenomeMaterializer | None = None,
        refiner: ReferenceArchitectureRefinement | None = None,
        observer: EvolutionObserver | None = None,
    ) -> None:
        self.constructor = constructor or ReferenceGenomeConstructor()
        self.evaluator = evaluator or ReferenceISRFitnessEvaluator()
        self.mutation_op = mutation_op or ReferenceMutationOperator()
        self.crossover_op = crossover_op or ReferenceCrossoverOperator()
        self.selector = selector or ReferenceParetoSelection()
        self.materializer = materializer or ReferenceGenomeMaterializer()
        self.refiner = refiner or ReferenceArchitectureRefinement()
        self.observer = observer or NullObserver()
        self.operations_trace: list[OperationRecord] = []

    def construct(self, isr: ISRRevision) -> Genome:
        return self.constructor.construct(isr)

    def evaluate_fitness(self, isr: ISRRevision, genome: Genome) -> FitnessVector:
        return self.evaluator.evaluate(isr, genome)

    def mutate_candidate(
        self, genome: Genome, rate: float, space: DecisionSpace
    ) -> Genome:
        result = self.mutation_op.mutate(genome, rate, space)
        self.operations_trace.append(
            OperationRecord(
                operation_type="mutation",
                source_genome_ids=[genome_content_hash(genome)],
                result_genome_id=genome_content_hash(result),
                mutation_rate=rate,
            )
        )
        return result

    def crossover_candidates(self, a: Genome, b: Genome) -> Genome:
        result = self.crossover_op.crossover(a, b)
        self.operations_trace.append(
            OperationRecord(
                operation_type="crossover",
                source_genome_ids=[
                    genome_content_hash(a),
                    genome_content_hash(b),
                ],
                result_genome_id=genome_content_hash(result),
            )
        )
        return result

    def select(self, candidates: list[FitnessVector]) -> int:
        return self.selector.select(candidates)

    def materialize_candidate(self, genome: Genome) -> ISRGraph:
        return self.materializer.materialize(genome)

    def refine_candidate(
        self, genome: Genome, weak_dims: list
    ) -> Genome:
        result = self.refiner.refine(genome, weak_dims)
        self.operations_trace.append(
            OperationRecord(
                operation_type="refinement",
                source_genome_ids=[genome_content_hash(genome)],
                result_genome_id=genome_content_hash(result),
            )
        )
        return result
