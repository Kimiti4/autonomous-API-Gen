"""Feedback-driven genome refinement (mutation of gene values per feedback dimension)."""

from __future__ import annotations

from evolution.core.fitness import FitnessDimension
from evolution.core.genome import Chromosome, ChromosomeFamily, Gene, Genome


class ReferenceArchitectureRefinement:
    """Deterministic refinement driven by FitnessDimension feedback."""

    def refine(
        self, genome: Genome, weak_dims: list[FitnessDimension]
    ) -> Genome:
        improvements: dict[str, str] = {
            FitnessDimension.MODULARITY.value: "domain-driven",
            FitnessDimension.SIMPLICITY.value: "modular",
            FitnessDimension.TESTABILITY.value: "contract-tested",
            FitnessDimension.SECURITY_POSTURE.value: "zero-trust",
            FitnessDimension.DEPLOYABILITY.value: "containerized",
        }

        new_chroms: dict[str, Chromosome] = {}
        for fam_key, chrom in genome.chromosomes.items():
            new_genes: dict[str, Gene] = {}
            for gid, gene in chrom.genes.items():
                if fam_key == ChromosomeFamily.ARCHITECTURE.value:
                    for dim in weak_dims:
                        if gene.decision == "decomposition" and dim.value in improvements:
                            new_genes[gid] = Gene(
                                gene_id=gid,
                                decision=gene.decision,
                                value=improvements[dim.value],
                            )
                            break
                    else:
                        new_genes[gid] = gene
                else:
                    new_genes[gid] = gene
            new_chroms[fam_key] = Chromosome(family=chrom.family, genes=new_genes)
        return Genome(system_id=genome.system_id, chromosomes=new_chroms)
