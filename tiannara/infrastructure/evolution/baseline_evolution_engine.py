from ...domain.ports import EvolutionEngine, EvolvedCandidate
from ...domain.models.genome import Genome
from ...domain.models.isr import IntermediateSoftwareRepresentation


class BaselineEvolutionEngine:
    """Baseline evolution: passes through with an explicit (non-mutating)
    rationale. Replace with a real Evolution Engine via the protocol."""

    def __init__(self, genome: Genome | None = None) -> None:
        self._genome = genome or Genome(generation=0)

    def evolve(self, isr: IntermediateSoftwareRepresentation) -> EvolvedCandidate:
        return EvolvedCandidate(
            genome=self._genome,
            rationale="Baseline pass-through; no mutation applied (generation 0).",
        )
