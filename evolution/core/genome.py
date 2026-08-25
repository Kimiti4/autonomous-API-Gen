"""Architectural genome: chromosomes, genes, and content-addressable hashing."""

from __future__ import annotations

import hashlib
import json
from enum import Enum
from typing import Any, Mapping

from pydantic import BaseModel, ConfigDict, Field


class ChromosomeFamily(str, Enum):
    ARCHITECTURE = "architecture"
    PERSISTENCE = "persistence"
    SECURITY = "security"
    MESSAGING = "messaging"
    INFRASTRUCTURE = "infrastructure"


class Gene(BaseModel):
    model_config = ConfigDict(frozen=True)

    gene_id: str = Field(min_length=1)
    decision: str = Field(min_length=1)
    value: str = Field(min_length=1)


class Chromosome(BaseModel):
    model_config = ConfigDict(frozen=True)

    family: ChromosomeFamily
    genes: Mapping[str, Gene] = Field(default_factory=dict)


class Genome(BaseModel):
    model_config = ConfigDict(frozen=True)

    system_id: str = Field(min_length=1)
    chromosomes: Mapping[str, Chromosome] = Field(default_factory=dict)


def genome_content_hash(genome: Genome) -> str:
    """Deterministic SHA-256 over the genome's canonical JSON form.

    Order-independent: genes within each chromosome are sorted by gene_id,
    chromosomes are sorted by family value.
    """
    canonical: dict[str, Any] = {"system_id": genome.system_id, "chromosomes": {}}
    for fam_key in sorted(genome.chromosomes.keys()):
        chrom = genome.chromosomes[fam_key]
        canonical["chromosomes"][fam_key] = {
            "family": chrom.family.value,
            "genes": {
                gid: gene.model_dump(mode="json")
                for gid, gene in sorted(chrom.genes.items())
            },
        }
    payload = json.dumps(
        canonical, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


class DecisionSpace(BaseModel):
    """Allowed values for each gene_id — the mutation search space."""

    choices: Mapping[str, list[str]] = Field(default_factory=dict)

    def values(self, gene_id: str) -> list[str]:
        return list(self.choices.get(gene_id, []))

    def is_valid(self, gene_id: str, value: str) -> bool:
        opts = self.choices.get(gene_id)
        return opts is None or value in opts
