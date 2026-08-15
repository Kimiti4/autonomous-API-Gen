"""
Runtime Learning Engine.

The closed loop behind Pass 10 (Runtime Instrumentation):

    watermarked telemetry -> SLO attainment -> fitness update
    -> directed mutation -> candidate genome -> (recompile via
    ProvenanceOrchestrator) -> redeploy

The engine is keyed by genome identity: every RuntimeObservation must carry
the genome_id that the running system was watermarked with (FastAPI span
attributes /health identity, Terraform resource tags). Misattributed
telemetry is rejected — provenance integrity is a precondition for learning.

Constitutional Alignment:
- Axiom II (Genome Isolation): candidates are produced by mutating genes
  only.
- Axiom VII (Auditability): every ingest is recorded as an append-only
  LearningIteration.
"""

from __future__ import annotations

from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

from constitutional_architecture.core.learning.fitness_update import (
    FitnessUpdateAlgorithm,
)
from constitutional_architecture.core.learning.models import (
    FitnessUpdate, LearningIteration, MutationDirective, RuntimeObservation,
)
from constitutional_architecture.core.models.genome import ArchitectureGenome
from constitutional_architecture.core.models.intent import QualityAttribute
from constitutional_architecture.core.models.isr import UniversalISR


class RuntimeLearningEngine:
    """Closed-loop learning over one deployed genome."""

    def __init__(
        self,
        genome: ArchitectureGenome,
        isr: UniversalISR,
        algorithm: Optional[FitnessUpdateAlgorithm] = None,
        quality_priorities: Optional[Mapping[QualityAttribute, float]] = None,
    ) -> None:
        self._genome = genome
        self._isr = isr
        self._algorithm = algorithm or FitnessUpdateAlgorithm()
        self._quality_priorities = dict(quality_priorities or {})
        self._iterations: List[LearningIteration] = []
        self._candidates: List[Tuple[ArchitectureGenome, List[MutationDirective]]] = []
        self._latest: Optional[FitnessUpdate] = None

    # ------------------------------------------------------------------
    # Ingest
    # ------------------------------------------------------------------

    def _verify_identity(self, genome_id: str) -> None:
        if genome_id != self._genome.genome_id:
            raise ValueError(
                f"Telemetry attributed to genome '{genome_id}' does not match "
                f"bound genome '{self._genome.genome_id}' — provenance "
                "integrity violated; rejecting observation"
            )

    def ingest(self, observation: RuntimeObservation) -> FitnessUpdate:
        """Ingest a watermarked telemetry window and run one learning step."""
        self._verify_identity(observation.genome_id)
        update = self._algorithm.evaluate(
            self._genome, self._isr, observation.endpoints,
            self._quality_priorities,
        )
        return self._record(update)

    def ingest_signals(
        self,
        dimension_scores: Mapping[str, float],
        genome_id: str = "",
        reasoning: str = "",
    ) -> FitnessUpdate:
        """Bridge from the Phase 6 sensory layer (FitnessSignal dimensions)."""
        if genome_id:
            self._verify_identity(genome_id)
        update = self._algorithm.evaluate_from_signals(
            self._genome, dimension_scores, reasoning)
        return self._record(update)

    def _record(self, update: FitnessUpdate) -> FitnessUpdate:
        previous = self._iterations[-1].final_fitness if self._iterations \
            else update.static_fitness
        iteration = LearningIteration(
            number=len(self._iterations) + 1,
            genome_id=update.genome_id,
            static_fitness=update.static_fitness,
            runtime_multiplier=update.runtime_multiplier,
            final_fitness=update.final_fitness,
            previous_fitness=previous,
            improvement=round(update.final_fitness - previous, 4),
            directives=update.directives,
            reasoning=update.reasoning,
        )
        self._iterations.append(iteration)
        self._latest = update
        return update

    # ------------------------------------------------------------------
    # Candidate production
    # ------------------------------------------------------------------

    def propose_candidate(
        self, max_severity: Optional[float] = None,
    ) -> Tuple[ArchitectureGenome, List[MutationDirective]]:
        """Produce the next candidate genome by applying the latest update's
        directives to a clone of the bound genome."""
        if self._latest is None:
            raise ValueError("No learning iteration recorded yet")
        candidate, applied = self._algorithm.apply_directives(
            self._genome, self._latest.directives, max_severity)
        self._candidates.append((candidate, applied))
        return candidate, applied

    # ------------------------------------------------------------------
    # State
    # ------------------------------------------------------------------

    @property
    def genome(self) -> ArchitectureGenome:
        return self._genome

    @property
    def iterations(self) -> Tuple[LearningIteration, ...]:
        return tuple(self._iterations)

    @property
    def candidates(self) -> Tuple[Tuple[ArchitectureGenome, List[MutationDirective]], ...]:
        return tuple(self._candidates)

    @property
    def latest_update(self) -> Optional[FitnessUpdate]:
        return self._latest

    @property
    def improvement(self) -> float:
        if len(self._iterations) < 2:
            return 0.0
        return self._iterations[-1].final_fitness - self._iterations[0].final_fitness

    def fitness_history(self) -> Tuple[float, ...]:
        return tuple(i.final_fitness for i in self._iterations)
