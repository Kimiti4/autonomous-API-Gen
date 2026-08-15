"""
Individual.

Represents a single member of the evolutionary population.
Each individual wraps an immutable ISR version with fitness, lineage, and metadata.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

from constitutional_architecture.engine.fitness import FitnessVector
from constitutional_architecture.isr.model.isr import ISR


@dataclass(frozen=True)
class Individual:
    """
    A single individual in the evolutionary population.

    Wraps an immutable ISR with evolutionary metadata.
    The ISR itself is never modified; new individuals are created
    through mutation and crossover.
    """

    # Core
    id: str
    isr: ISR
    fitness: FitnessVector = field(default_factory=lambda: FitnessVector(values={}))

    # Lineage
    parent_ids: tuple[str, ...] = ()
    generation: int = 0
    mutation_history: tuple[str, ...] = ()  # EIR IDs applied to produce this individual

    # Diversity
    species_id: str = ""
    novelty_score: float = 0.0

    # Lifecycle
    age: int = 0
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    is_elite: bool = False
    tags: tuple[str, ...] = ()

    # Fitness history
    fitness_history: tuple[FitnessVector, ...] = ()

    @property
    def isr_hash(self) -> str:
        return self.isr.content_hash

    @property
    def composite_fitness(self) -> float:
        return self.fitness.composite_score()

    def with_fitness(self, new_fitness: FitnessVector) -> "Individual":
        return Individual(
            id=self.id,
            isr=self.isr,
            fitness=new_fitness,
            parent_ids=self.parent_ids,
            generation=self.generation,
            mutation_history=self.mutation_history,
            species_id=self.species_id,
            novelty_score=self.novelty_score,
            age=self.age,
            created_at=self.created_at,
            is_elite=self.is_elite,
            tags=self.tags,
            fitness_history=self.fitness_history + (new_fitness,),
        )

    def with_age(self, new_age: int) -> "Individual":
        return Individual(
            id=self.id,
            isr=self.isr,
            fitness=self.fitness,
            parent_ids=self.parent_ids,
            generation=self.generation,
            mutation_history=self.mutation_history,
            species_id=self.species_id,
            novelty_score=self.novelty_score,
            age=new_age,
            created_at=self.created_at,
            is_elite=self.is_elite,
            tags=self.tags,
            fitness_history=self.fitness_history,
        )

    def with_species(self, species_id: str) -> "Individual":
        return Individual(
            id=self.id,
            isr=self.isr,
            fitness=self.fitness,
            parent_ids=self.parent_ids,
            generation=self.generation,
            mutation_history=self.mutation_history,
            species_id=species_id,
            novelty_score=self.novelty_score,
            age=self.age,
            created_at=self.created_at,
            is_elite=self.is_elite,
            tags=self.tags,
            fitness_history=self.fitness_history,
        )

    def with_elite(self, is_elite: bool = True) -> "Individual":
        return Individual(
            id=self.id,
            isr=self.isr,
            fitness=self.fitness,
            parent_ids=self.parent_ids,
            generation=self.generation,
            mutation_history=self.mutation_history,
            species_id=self.species_id,
            novelty_score=self.novelty_score,
            age=self.age,
            created_at=self.created_at,
            is_elite=is_elite,
            tags=self.tags,
            fitness_history=self.fitness_history,
        )
