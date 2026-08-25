"""Mutation and crossover Protocol seams + reference implementations."""

from __future__ import annotations

import random
from typing import Literal, Protocol

from evolution.core.fitness import FitnessDimension
from evolution.core.genome import Chromosome, ChromosomeFamily, DecisionSpace, Gene, Genome

OperationType = Literal["mutation", "crossover", "refinement"]


class MutationOperator(Protocol):
    def mutate(
        self, genome: Genome, mutation_rate: float, space: DecisionSpace
    ) -> Genome: ...


class CrossoverOperator(Protocol):
    def crossover(self, parent_a: Genome, parent_b: Genome) -> Genome: ...


class OperationRecord:
    """Traceability record for an evolution operation."""

    def __init__(
        self,
        operation_type: OperationType,
        source_genome_ids: list[str],
        result_genome_id: str,
        *,
        mutation_rate: float | None = None,
        changed_genes: list[str] | None = None,
    ) -> None:
        self.operation_type = operation_type
        self.source_genome_ids = list(source_genome_ids)
        self.result_genome_id = result_genome_id
        self.mutation_rate = mutation_rate
        self.changed_genes = list(changed_genes or [])


class ReferenceMutationOperator:
    """Uniform per-gene mutation within the DecisionSpace."""

    def __init__(self, rng: random.Random | None = None) -> None:
        self._rng = rng or random.Random()

    def mutate(
        self, genome: Genome, mutation_rate: float, space: DecisionSpace
    ) -> Genome:
        new_chroms: dict[str, Chromosome] = {}
        for fam_key, chrom in genome.chromosomes.items():
            new_genes: dict[str, Gene] = {}
            for gid, gene in chrom.genes.items():
                opts = [v for v in space.values(gid) if v != gene.value]
                if opts and self._rng.random() < mutation_rate:
                    new_val = self._rng.choice(opts)
                    new_genes[gid] = Gene(
                        gene_id=gid, decision=gene.decision, value=new_val
                    )
                else:
                    new_genes[gid] = gene
            new_chroms[fam_key] = Chromosome(family=chrom.family, genes=new_genes)
        return Genome(system_id=genome.system_id, chromosomes=new_chroms)


class ReferenceCrossoverOperator:
    """Uniform gene-wise crossover between two parent genomes."""

    def __init__(self, rng: random.Random | None = None) -> None:
        self._rng = rng or random.Random()

    def crossover(self, parent_a: Genome, parent_b: Genome) -> Genome:
        new_chroms: dict[str, Chromosome] = {}
        all_fams = set(parent_a.chromosomes) | set(parent_b.chromosomes)
        for fam_key in sorted(all_fams):
            ca = parent_a.chromosomes.get(fam_key)
            cb = parent_b.chromosomes.get(fam_key)
            if ca is None:
                new_chroms[fam_key] = cb  # type: ignore[assignment]
                continue
            if cb is None:
                new_chroms[fam_key] = ca
                continue
            all_genes = set(ca.genes) | set(cb.genes)
            merged_genes: dict[str, Gene] = {}
            for gid in sorted(all_genes):
                ga = ca.genes.get(gid)
                gb = cb.genes.get(gid)
                if ga is None:
                    merged_genes[gid] = gb  # type: ignore[assignment]
                elif gb is None:
                    merged_genes[gid] = ga
                else:
                    merged_genes[gid] = (
                        ga if self._rng.random() < 0.5 else gb
                    )
            family = ca.family if ca else cb.family  # type: ignore[union-attr]
            new_chroms[fam_key] = Chromosome(family=family, genes=merged_genes)
        return Genome(
            system_id=parent_a.system_id or parent_b.system_id,
            chromosomes=new_chroms,
        )
