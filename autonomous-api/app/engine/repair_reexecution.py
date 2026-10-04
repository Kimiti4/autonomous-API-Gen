"""Carry a verified repaired genome through dependent execution and measurements."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Mapping, Sequence, Any

from .dependency_reexecution import DependencyExecutionResult, execute_dependent_reverification
from .fullstack_genome import FullStackGenome
from .repair_coevolution import RepairExecution
from .specialized_mutations import EngineeringMutationSpec
from .cross_domain_evolution import CoEvolutionResult


@dataclass(frozen=True)
class RepairedCandidate:
    architecture: FullStackGenome
    dependency: DependencyExecutionResult


def reexecute_repaired_candidate(
    result: CoEvolutionResult,
    repair: RepairExecution,
    *,
    dependency_graph: Mapping[str, Sequence[str]],
    dependent_specs: tuple[EngineeringMutationSpec, ...],
    verifiers: Mapping[str, Any],
    observations: Mapping[str, Any],
    evidence_by_property: Mapping[str, tuple[str, ...]],
    successor_architecture_id: str,
) -> RepairedCandidate:
    dependency = execute_dependent_reverification(
        result,
        (repair,),
        dependency_graph,
        dependent_specs,
        verifiers,
        observations,
        evidence_by_property,
        successor_architecture_id=successor_architecture_id,
    )
    return RepairedCandidate(dependency.final_architecture, dependency)
