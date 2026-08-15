"""
Phase 10/11: Constitutional Memory & Taste Model.

High-fitness ISR snapshots are persisted. The Taste Model analyzes
successful snapshots to update Knowledge Graph weights and
Evaluator thresholds.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional

from constitutional_architecture.meta.genome.chromosomes import FrontendGenome
from constitutional_architecture.meta.genome.evaluators.i_fitness_evaluator import FitnessDimension


@dataclass(frozen=True)
class EvolutionarySnapshot:
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    genome: Optional[FrontendGenome] = None
    fitness_scores: tuple[FitnessDimension, ...] = ()
    pareto_rank: int = 0


class IConstitutionalMemory(ABC):
    @abstractmethod
    def save_snapshot(self, snapshot: EvolutionarySnapshot) -> None:
        ...

    @abstractmethod
    def get_high_performers(self, dimension: str, limit: int = 10) -> list[EvolutionarySnapshot]:
        ...

    @abstractmethod
    def get_all_snapshots(self) -> list[EvolutionarySnapshot]:
        ...


class InMemoryConstitutionalMemory(IConstitutionalMemory):
    def __init__(self) -> None:
        self._snapshots: list[EvolutionarySnapshot] = []

    def save_snapshot(self, snapshot: EvolutionarySnapshot) -> None:
        self._snapshots.append(snapshot)

    def get_high_performers(self, dimension: str, limit: int = 10) -> list[EvolutionarySnapshot]:
        filtered = [
            s for s in self._snapshots
            if any(d.name == dimension and d.score > 0.9 for d in s.fitness_scores)
        ]
        filtered.sort(key=lambda s: s.pareto_rank)
        return filtered[:limit]

    def get_all_snapshots(self) -> list[EvolutionarySnapshot]:
        return list(self._snapshots)

    @property
    def snapshot_count(self) -> int:
        return len(self._snapshots)


class TasteModelUpdater:
    def update_taste_weights(
        self,
        memory: IConstitutionalMemory,
        knowledge_graph: Any,
        dimension: str = "Design System Consistency",
    ) -> dict[str, Any]:
        winners = memory.get_high_performers(dimension, limit=50)
        if not winners:
            return {"updated": 0, "message": "No high-performer data available"}

        gene_values: dict[str, list[float]] = {}
        for snap in winners:
            if snap.genome is None:
                continue
            g = snap.genome
            for gene in g.all_genes:
                if isinstance(gene.allele, (int, float)):
                    if gene.id not in gene_values:
                        gene_values[gene.id] = []
                    gene_values[gene.id].append(float(gene.allele))

        trends: dict[str, dict[str, float]] = {}
        for gene_id, vals in gene_values.items():
            if vals:
                trends[gene_id] = {
                    "mean": sum(vals) / len(vals),
                    "min": min(vals),
                    "max": max(vals),
                    "count": len(vals),
                }

        return {"updated": len(trends), "trends": trends}
