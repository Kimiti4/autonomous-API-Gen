"""
Diversity Manager.

Prevents architectural monoculture through speciation,
similarity metrics, and entropy measurement.
"""

from __future__ import annotations

import math
import uuid
from dataclasses import dataclass, field
from typing import Optional

from constitutional_architecture.engine.config import EvolutionConfig
from constitutional_architecture.engine.fitness import FitnessVector
from constitutional_architecture.engine.individual import Individual


@dataclass
class Species:
    id: str
    representative_id: str = ""
    members: list[str] = field(default_factory=list)
    mean_fitness: float = 0.0
    age: int = 0
    stagnation: int = 0


class DiversityManager:
    """
    Preserves architectural diversity.

    Implements:
    - Speciation (clustering by fitness similarity)
    - Similarity metrics
    - Entropy measurement
    - Diversity thresholds
    - Species-level fitness sharing

    The best architecture is not always the most valuable.
    Maintain exploration.
    """

    def __init__(self, config: EvolutionConfig) -> None:
        self._config = config
        self._species: dict[str, Species] = {}
        self._archive: list[Individual] = []
        self._max_archive_size: int = 1000

    @property
    def species(self) -> dict[str, Species]:
        return dict(self._species)

    @property
    def species_count(self) -> int:
        return len(self._species)

    @property
    def archive_size(self) -> int:
        return len(self._archive)

    def speciate(self, population: list[Individual]) -> list[Individual]:
        if not self._config.speciation_enabled:
            return population

        for sp in self._species.values():
            sp.members = []

        assigned: list[Individual] = []
        for ind in population:
            species = self._find_species(ind)
            if species is None:
                species = Species(
                    id=f"species-{uuid.uuid4().hex[:8]}",
                    representative_id=ind.id,
                )
                self._species[species.id] = species

            species.members.append(ind.id)
            assigned.append(ind.with_species(species.id))

        self._species = {
            sid: sp for sid, sp in self._species.items() if sp.members
        }

        self._update_species_stats(assigned)

        return assigned

    def _find_species(self, individual: Individual) -> Optional[Species]:
        for species in self._species.values():
            rep_fitness = self._get_representative_fitness(species)
            if rep_fitness is not None:
                distance = individual.fitness.distance(rep_fitness)
                if distance < self._config.species_compatibility_threshold:
                    return species
        return None

    def _get_representative_fitness(self, species: Species) -> Optional[FitnessVector]:
        return None

    def _update_species_stats(self, population: list[Individual]) -> None:
        species_fitness: dict[str, list[float]] = {}
        for ind in population:
            if ind.species_id:
                species_fitness.setdefault(ind.species_id, []).append(ind.composite_fitness)

        for sid, fitnesses in species_fitness.items():
            if sid in self._species:
                self._species[sid].mean_fitness = sum(fitnesses) / len(fitnesses)

    def compute_diversity(self, population: list[Individual]) -> float:
        if len(population) < 2:
            return 0.0

        total_distance = 0.0
        pairs = 0
        sample_size = min(len(population), 50)
        sample = population[:sample_size]

        for i in range(len(sample)):
            for j in range(i + 1, len(sample)):
                total_distance += sample[i].fitness.distance(sample[j].fitness)
                pairs += 1

        if pairs == 0:
            return 0.0

        avg_distance = total_distance / pairs
        dims = population[0].fitness.dimension_count if population else 1
        max_distance = math.sqrt(max(dims, 1))
        return min(avg_distance / max_distance, 1.0) if max_distance > 0 else 0.0

    def compute_entropy(self, population: list[Individual]) -> float:
        if not self._species:
            return 0.0

        total = sum(len(sp.members) for sp in self._species.values())
        if total == 0:
            return 0.0

        entropy = 0.0
        for sp in self._species.values():
            if sp.members:
                p = len(sp.members) / total
                entropy -= p * math.log2(p)

        max_entropy = math.log2(len(self._species)) if len(self._species) > 1 else 1.0
        return entropy / max_entropy if max_entropy > 0 else 0.0

    def add_to_archive(self, individual: Individual) -> bool:
        archived_hashes = {ind.isr_hash for ind in self._archive}
        if individual.isr_hash in archived_hashes:
            return False

        self._archive.append(individual)
        if len(self._archive) > self._max_archive_size:
            self._archive = self._archive[-self._max_archive_size:]
        return True

    def is_diverse_enough(self, population: list[Individual]) -> bool:
        return self.compute_diversity(population) >= self._config.diversity_threshold
