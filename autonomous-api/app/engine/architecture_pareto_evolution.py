"""Evidence-bounded Pareto architecture evolution across generations.

This layer evolves an architecture population without selecting a single winner.
Only evidence-backed members are eligible, lineage must point to known parents, and
the result remains a Pareto frontier rather than an arbitrary best architecture.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from .evolution_population import EvolutionMember, EvolutionPopulation, promote_frontier
from .pareto_architecture import Objective


@dataclass(frozen=True)
class ArchitectureEvolutionResult:
    previous_generation: int
    next_generation: int
    population: EvolutionPopulation
    retained_ids: tuple[str, ...]
    admitted_ids: tuple[str, ...]
    rejected_ids: tuple[str, ...]
    status: str
    rationale: str


def evolve_architecture_population(
    population: EvolutionPopulation,
    offspring: Sequence[EvolutionMember],
    objectives: Sequence[Objective],
) -> ArchitectureEvolutionResult:
    """Admit verified offspring and retain only the next-generation Pareto frontier.

    This function never mutates the input population and never chooses a single
    global optimum. Offspring must belong to exactly the next generation and
    every parent reference must resolve to the current generation or to an
    already-admitted offspring. A missing/invalid lineage fails closed.
    """
    if not objectives:
        raise ValueError("evolution-requires-objectives")
    if population.generation < 0:
        raise ValueError("invalid-generation")

    next_generation = population.generation + 1
    current_ids = {m.lineage.architecture_id for m in population.members}
    if len(current_ids) != len(population.members):
        raise ValueError("population-requires-unique-architecture-ids")

    offspring_ids = [m.lineage.architecture_id for m in offspring]
    if len(set(offspring_ids)) != len(offspring_ids):
        raise ValueError("offspring-requires-unique-architecture-ids")
    if current_ids.intersection(offspring_ids):
        raise ValueError("offspring-id-collides-with-parent")

    known_ids = set(current_ids)
    rejected: list[str] = []
    admitted: list[EvolutionMember] = []

    for child in offspring:
        child_id = child.lineage.architecture_id
        if child.lineage.generation != next_generation:
            rejected.append(child_id)
            continue
        if not child.score.evidence or not child.lineage.evidence:
            rejected.append(child_id)
            continue
        if not set(child.lineage.parent_ids).issubset(known_ids):
            rejected.append(child_id)
            continue
        admitted.append(child)
        known_ids.add(child_id)

    if rejected:
        raise ValueError("evolution-lineage-or-evidence-invalid:" + ",".join(sorted(rejected)))

    combined = tuple(population.members) + tuple(admitted)
    next_population = promote_frontier(combined, objectives, next_generation)
    frontier_ids = tuple(m.lineage.architecture_id for m in next_population.members)

    return ArchitectureEvolutionResult(
        population.generation,
        next_generation,
        next_population,
        tuple(sorted(set(current_ids).intersection(frontier_ids))),
        tuple(sorted(set(offspring_ids).intersection(frontier_ids))),
        (),
        "evolved",
        "Admitted evidence-backed offspring and retained the non-dominated Pareto frontier; no single global optimum was selected.",
    )
