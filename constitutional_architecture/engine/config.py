"""
Evolution Configuration.

All configuration for an evolution run. Frozen to guarantee reproducibility.
Given the same config and initial ISR, the engine produces identical results.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional


@dataclass(frozen=True)
class EvolutionConfig:
    """
    Immutable configuration for a single evolution run.

    Frozen to guarantee reproducibility. No parameter may change mid-run.
    """

    # Identity
    run_id: str = ""
    seed: int = 42

    # Population
    population_size: int = 50
    elite_count: int = 5
    max_generations: int = 100

    # Mutation
    mutation_rate: float = 0.3
    crossover_rate: float = 0.2
    max_mutations_per_individual: int = 3

    # Selection
    selection_algorithm: str = "tournament"  # "tournament" | "roulette" | "rank"
    tournament_size: int = 5

    # Diversity
    diversity_threshold: float = 0.15
    novelty_weight: float = 0.1
    speciation_enabled: bool = True
    species_compatibility_threshold: float = 0.3

    # Convergence
    convergence_window: int = 20
    convergence_threshold: float = 0.001
    stagnation_limit: int = 30

    # Fitness
    fitness_dimensions: tuple[str, ...] = (
        "complexity",
        "coupling",
        "cohesion",
        "security_coverage",
        "scalability",
        "reliability",
        "deployment_completeness",
        "observability",
        "documentation",
        "maintainability",
        "extensibility",
        "architecture_quality",
    )

    # Adaptive mutation
    adaptive_learning_rate: float = 0.05
    adaptive_min_weight: float = 0.01
    adaptive_max_weight: float = 1.0

    # Knowledge base
    knowledge_base_enabled: bool = True
    knowledge_base_version: str = ""

    # Reproducibility
    deterministic: bool = True

    # Metadata
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    description: str = ""

    def __post_init__(self) -> None:
        if self.population_size < 2:
            raise ValueError("Population size must be at least 2")
        if self.elite_count >= self.population_size:
            raise ValueError("Elite count must be less than population size")
        if not 0.0 <= self.mutation_rate <= 1.0:
            raise ValueError("Mutation rate must be in [0.0, 1.0]")
        if not 0.0 <= self.crossover_rate <= 1.0:
            raise ValueError("Crossover rate must be in [0.0, 1.0]")
