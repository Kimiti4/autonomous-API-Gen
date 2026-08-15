from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from constitutional_architecture.core.models.genome import ArchitectureGenome


@dataclass
class MutationEvent:
    gene_id: str
    gene_name: str
    gene_type: str
    old_value: Any
    new_value: Any


class GenomeMutator:
    """System-level mutation operator for the ArchitectureGenome."""

    def __init__(self, rng: Optional[random.Random] = None) -> None:
        self._rng = rng or random.Random()
        self._history: List[MutationEvent] = []

    def mutate(self, genome: ArchitectureGenome, rate: float = 0.1) -> ArchitectureGenome:
        new_genome = genome.clone()
        mutations = new_genome.mutate(rate, self._rng)

        for gene_id in genome.categorical_genes:
            old_val = genome.categorical_genes[gene_id].value
            new_val = new_genome.categorical_genes[gene_id].value
            if old_val != new_val:
                self._history.append(MutationEvent(
                    gene_id=gene_id,
                    gene_name=genome.categorical_genes[gene_id].name,
                    gene_type="categorical",
                    old_value=old_val,
                    new_value=new_val,
                ))

        for gene_id in genome.continuous_genes:
            old_val = genome.continuous_genes[gene_id].value
            new_val = new_genome.continuous_genes[gene_id].value
            if old_val != new_val:
                self._history.append(MutationEvent(
                    gene_id=gene_id,
                    gene_name=genome.continuous_genes[gene_id].name,
                    gene_type="continuous",
                    old_value=old_val,
                    new_value=new_val,
                ))

        return new_genome

    def mutate_weighted(self, genome: ArchitectureGenome,
                        weights: Dict[str, float]) -> ArchitectureGenome:
        new_genome = genome.clone()
        for gene_id, weight in weights.items():
            if gene_id in new_genome.categorical_genes:
                if self._rng.random() < weight:
                    new_genome.categorical_genes[gene_id].mutate(1.0, self._rng)
            elif gene_id in new_genome.continuous_genes:
                if self._rng.random() < weight:
                    new_genome.continuous_genes[gene_id].mutate(1.0, self._rng)
        return new_genome

    @property
    def history(self) -> List[MutationEvent]:
        return list(self._history)

    def clear_history(self) -> None:
        self._history.clear()
