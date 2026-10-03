"""Evidenced Pareto frontier as an evolvable architectural population."""
from __future__ import annotations
from dataclasses import dataclass
from .pareto_architecture import ArchitectureScore, Objective, build_frontier


@dataclass(frozen=True)
class Lineage:
    architecture_id: str
    parent_ids: tuple[str, ...]
    generation: int
    evidence: tuple[str, ...]


@dataclass(frozen=True)
class PopulationMember:
    score: ArchitectureScore
    lineage: Lineage
    active: bool = True


@dataclass(frozen=True)
class EvolutionPopulation:
    members: tuple[PopulationMember, ...]
    generation: int


def seed_population(scores: tuple[ArchitectureScore, ...]) -> EvolutionPopulation:
    if not scores:
        raise ValueError("population-requires-seeds")
    return EvolutionPopulation(
        tuple(
            PopulationMember(
                score=s,
                lineage=Lineage(s.architecture_id, (), 0, s.evidence),
            )
            for s in scores
        ),
        0,
    )


def select_frontier(
    population: EvolutionPopulation,
    objectives: tuple[Objective, ...],
) -> EvolutionPopulation:
    active = tuple(m for m in population.members if m.active)
    result = build_frontier(tuple(m.score for m in active), objectives)
    keep = set(result.frontier)
    return EvolutionPopulation(
        tuple(
            PopulationMember(m.score, m.lineage, m.score.architecture_id in keep)
            for m in active
        ),
        population.generation,
    )


def add_offspring(
    population: EvolutionPopulation,
    offspring: tuple[PopulationMember, ...],
) -> EvolutionPopulation:
    if any(m.lineage.generation <= population.generation for m in offspring):
        raise ValueError("offspring-generation-must-increase")
    ids = {m.score.architecture_id for m in population.members}
    if any(m.score.architecture_id in ids for m in offspring):
        raise ValueError("duplicate-architecture-id")
    return EvolutionPopulation(
        population.members + offspring,
        max(m.lineage.generation for m in offspring),
    )


def crossover(
    left: PopulationMember,
    right: PopulationMember,
    child_id: str,
    child_score: ArchitectureScore,
) -> PopulationMember:
    if left.score.architecture_id == right.score.architecture_id:
        raise ValueError("crossover-requires-distinct-parents")
    if not child_score.evidence:
        raise ValueError("offspring-requires-evidence")
    return PopulationMember(
        child_score,
        Lineage(
            child_id,
            (left.score.architecture_id, right.score.architecture_id),
            max(left.lineage.generation, right.lineage.generation) + 1,
            child_score.evidence,
        ),
    )
