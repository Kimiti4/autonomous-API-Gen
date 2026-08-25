"""Reference ISR-based fitness evaluator (structural heuristics only)."""

from __future__ import annotations

from evolution.core.fitness import FitnessDimension, FitnessVector
from evolution.core.genome import ChromosomeFamily, Genome
from isr.core.graph import NodeType
from isr.core.revision import ISRRevision


class ReferenceISRFitnessEvaluator:
    """Evaluate genome quality from ISR structure alone (no external systems)."""

    def evaluate(self, isr: ISRRevision, genome: Genome) -> FitnessVector:
        n = len(isr.graph.nodes)
        e = len(isr.graph.edges)
        domains = sum(1 for nd in isr.graph.nodes.values() if nd.type == NodeType.DOMAIN)
        services = sum(1 for nd in isr.graph.nodes.values() if nd.type == NodeType.SERVICE)

        modularity = min(1.0, domains / 3.0) if domains > 0 else 0.0
        simplicity = max(0.0, 1.0 - e / 20.0) if e > 0 else 1.0
        testability = 1.0 if services > 0 else 0.0

        has_sec = ChromosomeFamily.SECURITY.value in genome.chromosomes
        security_posture = 1.0 if has_sec else 0.0

        has_persist = ChromosomeFamily.PERSISTENCE.value in genome.chromosomes
        deployability = 1.0 if (has_persist and has_sec) else 0.5

        return FitnessVector(
            scores={
                FitnessDimension.MODULARITY: round(modularity, 4),
                FitnessDimension.SIMPLICITY: round(simplicity, 4),
                FitnessDimension.TESTABILITY: round(testability, 4),
                FitnessDimension.SECURITY_POSTURE: round(security_posture, 4),
                FitnessDimension.DEPLOYABILITY: round(deployability, 4),
            }
        )
