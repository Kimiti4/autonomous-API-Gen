"""Bridge full-stack genome operators into an evolutionary population."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Callable
from .fullstack_genome import FullStackGenome
from .fullstack_mutation import compatibility_errors, recombine


@dataclass(frozen=True)
class GenomeIndividual:
    individual_id: str
    genome: FullStackGenome
    parent_ids: tuple[str, ...] = ()


@dataclass(frozen=True)
class PopulationGeneration:
    generation: int
    individuals: tuple[GenomeIndividual, ...]


def validate_individual(individual: GenomeIndividual) -> tuple[str, ...]:
    return compatibility_errors(individual.genome)


def mutate_individual(
    individual: GenomeIndividual,
    individual_id: str,
    mutator: Callable[[FullStackGenome], FullStackGenome],
) -> GenomeIndividual:
    genome = mutator(individual.genome)
    errors = compatibility_errors(genome)
    if errors:
        raise ValueError("invalid-offspring:" + ";".join(errors))
    return GenomeIndividual(individual_id, genome, (individual.individual_id,))


def crossover_individuals(
    left: GenomeIndividual,
    right: GenomeIndividual,
    individual_id: str,
) -> GenomeIndividual:
    genome = recombine(left.genome, right.genome)
    errors = compatibility_errors(genome)
    if errors:
        raise ValueError("invalid-offspring:" + ";".join(errors))
    return GenomeIndividual(
        individual_id,
        genome,
        (left.individual_id, right.individual_id),
    )


def next_generation(
    previous: PopulationGeneration,
    offspring: tuple[GenomeIndividual, ...],
    generation: int | None = None,
) -> PopulationGeneration:
    accepted = tuple(i for i in offspring if not validate_individual(i))
    return PopulationGeneration(
        previous.generation + 1 if generation is None else generation,
        accepted,
    )
