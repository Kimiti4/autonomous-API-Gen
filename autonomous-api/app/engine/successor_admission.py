"""Materialize an evidence-backed successor event and admit it to the next generation."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Mapping, Sequence
from .cross_domain_evolution import CoEvolutionEvent, CoEvolutionResult, DomainChange
from .dependency_reexecution import DependencyExecutionResult
from .evolution_population import EvolutionMember, spawn_mutation, EvolutionPopulation, promote_frontier
from .pareto_architecture import ArchitectureScore, Objective, build_frontier
from .repair_coevolution import RepairExecution
from .repair_closure import RepairClosure


@dataclass(frozen=True)
class SuccessorEvent:
    event: CoEvolutionEvent
    architecture_id: str
    parent_event_id: str
    evidence: tuple[str, ...]
    reports: tuple[object, ...]
    passed: bool


@dataclass(frozen=True)
class SuccessorAdmission:
    event: SuccessorEvent
    member: EvolutionMember
    population: EvolutionPopulation


def materialize_successor_event(
    source: CoEvolutionResult,
    dependency_result: DependencyExecutionResult,
    *,
    event_id: str,
    source_member: EvolutionMember,
    score: ArchitectureScore,
) -> SuccessorEvent:
    closure = dependency_result.closure
    if not closure.admissible:
        raise ValueError("successor-closure-not-admissible:" + ",".join(closure.residuals))
    if score.architecture_id != dependency_result.closure.successor_architecture_id:
        raise ValueError("successor-score-id-mismatch")

    changes = tuple(
        DomainChange(r.candidate.domain, r.candidate.repair_mutation_id, r.candidate.counterexample_properties)
        for r in closure.repairs
    ) + tuple(
        DomainChange(x.domain, x.mutation_id, tuple(g.property_name for g in x.verification.results))
        for x in dependency_result.executions
    )
    if not changes:
        raise ValueError("successor-requires-changes")

    evidence = set(source.event.evidence)
    for repair in closure.repairs:
        evidence.update(repair.verification.results[i].evidence[0]
                       for i in range(len(repair.verification.results))
                       if repair.verification.results[i].evidence)
    for execution in dependency_result.executions:
        for gate in execution.verification.results:
            evidence.update(gate.evidence)
    evidence.update(score.evidence)

    event = CoEvolutionEvent(
        event_id,
        source.architecture_id,
        changes,
        tuple(sorted(evidence)),
    )
    reports = tuple(r.verification for r in closure.repairs) + tuple(
        x.verification for x in dependency_result.executions
    )
    return SuccessorEvent(
        event,
        score.architecture_id,
        source.event.event_id,
        tuple(sorted(evidence)),
        reports,
        all(r.passed for r in reports),
    )


def admit_successor(
    source_member: EvolutionMember,
    successor: SuccessorEvent,
    score: ArchitectureScore,
    objectives: tuple[Objective, ...],
    generation: int,
) -> SuccessorAdmission:
    if not successor.passed:
        raise ValueError("successor-verification-failed")
    if successor.architecture_id != score.architecture_id:
        raise ValueError("successor-score-id-mismatch")
    candidate = spawn_mutation(source_member, successor.architecture_id, score, generation)
    frontier = build_frontier((source_member.score, candidate.score), objectives)
    if candidate.lineage.architecture_id not in frontier.frontier:
        raise ValueError("successor-dominated")
    population = promote_frontier((source_member, candidate), objectives, generation)
    return SuccessorAdmission(successor, candidate, population)
