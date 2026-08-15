"""
Frontend Design Genome — Evolutionary Operators.

Operators are specialized to mimic senior design iteration:
- Bounded Continuous Mutation: mutate HSL parameters within perceptual bounds
- Semantic Crossover (The "Mashup" Operator): swap entire chromosomes between parents
- Heuristic Mutation: targeted mutations based on proven patterns (from Design Knowledge Graph)
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Optional

from constitutional_architecture.meta.genome.chromosomes import (
    FrontendGenome, PresentationChromosome, StructureChromosome,
    BehaviorChromosome, CompositionChromosome, ComplianceChromosome,
)


@dataclass
class MutationRecord:
    gene_id: str
    gene_name: str
    chromosome_family: str
    old_allele: object
    new_allele: object
    mutation_type: str


@dataclass
class CrossoverRecord:
    parent_a_id: int
    parent_b_id: int
    swapped_chromosomes: list[str]


class FrontendMutator:
    """Applies bounded, design-aware mutations to a frontend genome.

    Mimics senior designer iteration rather than random noise.
    """

    def __init__(self, rng: Optional[random.Random] = None) -> None:
        self._rng = rng or random.Random()
        self._history: list[MutationRecord] = []

    def mutate(self, genome: FrontendGenome, rate: float = 0.1) -> FrontendGenome:
        new_genome = genome.clone()
        new_genome.mutate(rate, self._rng)
        return new_genome

    def mutate_bounded(self, genome: FrontendGenome, rate: float = 0.1,
                       target_gene_id: Optional[str] = None) -> FrontendGenome:
        new_genome = genome.clone()
        for gene in new_genome.all_genes:
            if target_gene_id and gene.id != target_gene_id:
                continue
            old = gene.allele
            gene.mutate(rate, self._rng)
            if old != gene.allele:
                self._history.append(MutationRecord(
                    gene_id=gene.id, gene_name=gene.name,
                    chromosome_family=gene.chromosome_family,
                    old_allele=old, new_allele=gene.allele,
                    mutation_type=gene.mutation_type.value,
                ))
        return new_genome

    def heuristic_mutate(self, genome: FrontendGenome,
                         heuristics: list[dict[str, object]]) -> FrontendGenome:
        new_genome = genome.clone()
        for heuristic in heuristics:
            gene_id = heuristic.get("target_gene_id", "")
            new_value = heuristic.get("new_allele")
            for gene in new_genome.all_genes:
                if gene.id == gene_id:
                    old = gene.allele
                    try:
                        cloned = gene.clone(new_value)
                        setattr(gene, "_allele", cloned.allele)
                    except (ValueError, TypeError):
                        pass
                    self._history.append(MutationRecord(
                        gene_id=gene.id, gene_name=gene.name,
                        chromosome_family=gene.chromosome_family,
                        old_allele=old, new_allele=gene.allele,
                        mutation_type="heuristic",
                    ))
                    break
        return new_genome

    @property
    def history(self) -> list[MutationRecord]:
        return list(self._history)

    def clear_history(self) -> None:
        self._history.clear()


class FrontendCrossover:
    """Semantic crossover — swaps entire chromosome families between parents.

    The "Mashup" Operator: a novel architecture that inherits the structural
    rigor of one parent and the visual appeal of another.
    """

    def __init__(self, rng: Optional[random.Random] = None) -> None:
        self._rng = rng or random.Random()
        self._history: list[CrossoverRecord] = []

    def single_point(self, parent_a: FrontendGenome, parent_b: FrontendGenome,
                     rate: float = 0.5) -> tuple[FrontendGenome, FrontendGenome]:
        """Swaps one randomly selected chromosome family between parents."""
        families = ["presentation", "structure", "behavior", "composition", "compliance"]
        if self._rng.random() > rate:
            return parent_a.clone(), parent_b.clone()

        chosen = self._rng.choice(families)
        child_a, child_b = parent_a.clone(), parent_b.clone()
        a_chromo = getattr(child_a, chosen)
        b_chromo = getattr(child_b, chosen)
        setattr(child_a, chosen, b_chromo)
        setattr(child_b, chosen, a_chromo)

        self._history.append(CrossoverRecord(
            parent_a_id=id(parent_a), parent_b_id=id(parent_b),
            swapped_chromosomes=[chosen],
        ))
        return child_a, child_b

    def multi_point(self, parent_a: FrontendGenome, parent_b: FrontendGenome,
                    rate: float = 0.3) -> tuple[FrontendGenome, FrontendGenome]:
        """Swaps multiple randomly selected chromosomes between parents."""
        families = ["presentation", "structure", "behavior", "composition", "compliance"]
        if self._rng.random() > rate:
            return parent_a.clone(), parent_b.clone()

        child_a, child_b = parent_a.clone(), parent_b.clone()
        swapped: list[str] = []
        for fam in families:
            if self._rng.random() < 0.5:
                a_chromo = getattr(child_a, fam)
                b_chromo = getattr(child_b, fam)
                setattr(child_a, fam, b_chromo)
                setattr(child_b, fam, a_chromo)
                swapped.append(fam)

        self._history.append(CrossoverRecord(
            parent_a_id=id(parent_a), parent_b_id=id(parent_b),
            swapped_chromosomes=swapped,
        ))
        return child_a, child_b

    @property
    def history(self) -> list[CrossoverRecord]:
        return list(self._history)

    def clear_history(self) -> None:
        self._history.clear()
