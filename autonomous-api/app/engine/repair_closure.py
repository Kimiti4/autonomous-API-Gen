"""Close dependent-domain repair, re-execution, and evolutionary admission."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Any, Sequence

from .cross_domain_evolution import CoEvolutionResult
from .evolution_population import EvolutionMember, spawn_mutation, EvolutionPopulation, promote_frontier
from .fullstack_genome import FullStackGenome
from .pareto_architecture import ArchitectureScore, Objective, build_frontier
from .repair_coevolution import Counterexample, RepairExecution, extract_counterexamples
from .specialized_mutations import EngineeringMutationSpec
from .verification_plans import VerificationReport


@dataclass(frozen=True)
class DependencyInvalidation:
    failed_domain: str
    invalidated_domains: tuple[str, ...]
    evidence: tuple[str, ...]


@dataclass(frozen=True)
class SuccessorDomainVerification:
    domain: str
    mutation_id: str
    verification: VerificationReport


@dataclass(frozen=True)
class RepairClosure:
    source_event_id: str
    source_architecture_id: str
    counterexamples: tuple[Counterexample, ...]
    invalidation: DependencyInvalidation
    repairs: tuple[RepairExecution, ...]
    dependent_reverification: tuple[SuccessorDomainVerification, ...]
    successor_architecture_id: str | None
    admissible: bool
    residuals: tuple[str, ...]


def _dependency_closure(
    failed_domains: set[str],
    dependency_graph: Mapping[str, Sequence[str]],
) -> set[str]:
    closure = set(failed_domains)
    changed = True
    while changed:
        changed = False
        for source, targets in dependency_graph.items():
            if source in closure:
                for target in targets:
                    if target not in closure:
                        closure.add(target)
                        changed = True
    return closure


def close_repair_and_dependencies(
    result: CoEvolutionResult,
    repairs: tuple[RepairExecution, ...],
    dependency_graph: Mapping[str, Sequence[str]],
    dependent_reports: tuple[SuccessorDomainVerification, ...],
    *,
    successor_architecture_id: str | None = None,
) -> RepairClosure:
    counterexamples = extract_counterexamples(result)
    failed_domains = {cx.domain for cx in counterexamples}
    invalidated = _dependency_closure(failed_domains, dependency_graph)

    evidence = tuple(sorted({
        e
        for cx in counterexamples
        for e in cx.evidence
    }))
    residuals = []

    repaired_domains = {r.candidate.domain for r in repairs}
    for domain in sorted(failed_domains - repaired_domains):
        residuals.append("unrepaired-domain:" + domain)

    report_domains = {r.domain for r in dependent_reports}
    for domain in sorted(invalidated - report_domains):
        residuals.append("missing-dependent-reverification:" + domain)

    if repairs:
        for repair in repairs:
            if not repair.verification.passed:
                residuals.append("repair-verification-failed:" + repair.candidate.domain)

    admissible = not residuals
    if admissible and not successor_architecture_id:
        residuals.append("missing-successor-architecture-id")
        admissible = False

    return RepairClosure(
        result.event.event_id,
        result.event.source_architecture_id,
        counterexamples,
        DependencyInvalidation(
            next(iter(sorted(failed_domains))) if failed_domains else "",
            tuple(sorted(invalidated)),
            evidence,
        ),
        repairs,
        dependent_reports,
        successor_architecture_id if admissible else None,
        admissible,
        tuple(sorted(set(residuals))),
    )


def admit_repaired_candidate(
    parent: EvolutionMember,
    closure: RepairClosure,
    score: ArchitectureScore,
    generation: int,
    objectives: tuple[Objective, ...],
) -> EvolutionMember:
    if not closure.admissible:
        raise ValueError("repair-closure-not-admissible:" + ",".join(closure.residuals))
    if closure.successor_architecture_id != score.architecture_id:
        raise ValueError("successor-score-id-mismatch")

    candidate = spawn_mutation(
        parent,
        score.architecture_id,
        score,
        generation,
    )
    frontier = build_frontier((parent.score, candidate.score), objectives)
    if candidate.lineage.architecture_id not in frontier.frontier:
        raise ValueError("successor-dominated")
    return candidate
