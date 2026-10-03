"""Promote evidence-backed Pareto architectures into lineage-preserving populations."""
from __future__ import annotations
from dataclasses import dataclass
from .pareto_architecture import ArchitectureScore, build_frontier


@dataclass(frozen=True)
class ArchitectureLineage:
    architecture_id: str
    parent_ids: tuple[str, ...]
    generation: int
    evidence: tuple[str, ...]


@dataclass(frozen=True)
class EvolutionMember:
    lineage: ArchitectureLineage
    score: ArchitectureScore


@dataclass(frozen=True)
class EvolutionPopulation:
    generation: int
    members: tuple[EvolutionMember, ...]


def promote_frontier(members, objectives, generation: int) -> EvolutionPopulation:
    if generation < 0:
        raise ValueError("invalid-generation")
    if not members:
        raise ValueError("population-requires-members")
    frontier = build_frontier(tuple(m.score for m in members), objectives)
    kept = tuple(m for m in members if m.lineage.architecture_id in frontier.frontier)
    return EvolutionPopulation(generation, kept)


def spawn_mutation(parent, child_id, score, generation: int) -> EvolutionMember:
    if generation <= parent.lineage.generation:
        raise ValueError("child-generation-must-increase")
    if score.architecture_id != child_id:
        raise ValueError("child-score-id-mismatch")
    if not score.evidence:
        raise ValueError("child-requires-evidence")
    return EvolutionMember(
        ArchitectureLineage(child_id, (parent.lineage.architecture_id,), generation, score.evidence),
        score,
    )


def crossover(left, right, child_id, score, generation: int) -> EvolutionMember:
    if left.lineage.architecture_id == right.lineage.architecture_id:
        raise ValueError("crossover-requires-distinct-parents")
    if generation <= max(left.lineage.generation, right.lineage.generation):
        raise ValueError("child-generation-must-increase")
    if score.architecture_id != child_id:
        raise ValueError("child-score-id-mismatch")
    if not score.evidence:
        raise ValueError("child-requires-evidence")
    return EvolutionMember(
        ArchitectureLineage(
            child_id,
            tuple(sorted((left.lineage.architecture_id, right.lineage.architecture_id))),
            generation,
            score.evidence,
        ),
        score,
    )
