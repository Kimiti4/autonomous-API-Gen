"""
Novelty Search.

Discovers unusual architectures regardless of current fitness.
Prevents premature convergence by rewarding exploration.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from constitutional_architecture.engine.fitness import FitnessVector
from constitutional_architecture.engine.individual import Individual


@dataclass(frozen=True)
class NoveltyResult:
    novelty_score: float
    nearest_neighbors: tuple[str, ...] = ()
    is_novel: bool = False


class NoveltySearch:
    """
    Novelty search for architectural exploration.

    Computes novelty as the average distance to the k nearest
    neighbours in the archive of previously seen architectures.

    High novelty = architecturally unusual = worth exploring.
    """

    def __init__(
        self,
        k_neighbors: int = 15,
        novelty_threshold: float = 0.3,
        archive_limit: int = 5000,
    ) -> None:
        self._k = k_neighbors
        self._threshold = novelty_threshold
        self._archive: list[Individual] = []
        self._archive_limit = archive_limit

    @property
    def archive_size(self) -> int:
        return len(self._archive)

    def compute_novelty(
        self,
        individual: Individual,
        population: Optional[list[Individual]] = None,
    ) -> NoveltyResult:
        references = list(self._archive)
        if population:
            references.extend(population)

        if len(references) < self._k:
            return NoveltyResult(novelty_score=1.0, is_novel=True)

        distances: list[tuple[float, str]] = []
        for ref in references:
            if ref.id == individual.id:
                continue
            try:
                dist = individual.fitness.distance(ref.fitness)
                distances.append((dist, ref.id))
            except ValueError:
                continue

        if not distances:
            return NoveltyResult(novelty_score=1.0, is_novel=True)

        distances.sort(key=lambda x: x[0])
        k_nearest = distances[:self._k]

        avg_distance = sum(d for d, _ in k_nearest) / len(k_nearest)
        neighbor_ids = tuple(ref_id for _, ref_id in k_nearest[:5])

        is_novel = avg_distance >= self._threshold

        return NoveltyResult(
            novelty_score=avg_distance,
            nearest_neighbors=neighbor_ids,
            is_novel=is_novel,
        )

    def add_to_archive(self, individual: Individual) -> None:
        self._archive.append(individual)
        if len(self._archive) > self._archive_limit:
            self._archive = self._archive[-self._archive_limit:]

    def update_novelty_scores(self, population: list[Individual]) -> list[Individual]:
        updated: list[Individual] = []
        for ind in population:
            result = self.compute_novelty(ind, population)
            new_ind = Individual(
                id=ind.id,
                isr=ind.isr,
                fitness=ind.fitness,
                parent_ids=ind.parent_ids,
                generation=ind.generation,
                mutation_history=ind.mutation_history,
                species_id=ind.species_id,
                novelty_score=result.novelty_score,
                age=ind.age,
                created_at=ind.created_at,
                is_elite=ind.is_elite,
                tags=ind.tags,
                fitness_history=ind.fitness_history,
            )
            updated.append(new_ind)
            if result.is_novel:
                self.add_to_archive(ind)
        return updated
