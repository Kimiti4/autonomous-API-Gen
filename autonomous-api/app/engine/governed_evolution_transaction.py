"""Governed entry point for Bucket 2 capability-aware evolution."""

from __future__ import annotations

from typing import Any, Mapping, Sequence

from .capability_contract import WorkCapabilityContract, validate_work_capability
from .evolution_transaction import EvolutionTransaction, execute_evolution_transaction
from .scope_authorization import MutationIntent
from .specialized_mutations import EngineeringMutationSpec
from .fullstack_genome import FullStackGenome
from .cross_domain_evolution import CoEvolutionResult
from .evolution_population import EvolutionMember
from .pareto_architecture import Objective
from .transaction_verification import TransactionVerificationConfig
from .work_mode_scope_validation import validate_mode_surface
from .capability_domain_resolution import validate_mutation_domains


def execute_governed_evolution_transaction(
    capability: WorkCapabilityContract,
    *,
    mutations: tuple[MutationIntent, ...],
    source: CoEvolutionResult,
    source_member: EvolutionMember,
    genome: FullStackGenome,
    repair_specs: tuple[EngineeringMutationSpec, ...],
    dependent_specs: tuple[EngineeringMutationSpec, ...],
    dependency_graph: Mapping[str, Sequence[str]],
    verifiers: Mapping[str, Any],
    observations: Mapping[str, Any],
    evidence_by_property: Mapping[str, tuple[str, ...]],
    objectives: tuple[Objective, ...],
    measurement_runners: Mapping[str, Any],
    measurement_context: Mapping[str, Any],
    event_id: str,
    successor_architecture_id: str,
    generation: int,
    verification_config: TransactionVerificationConfig,
    verification_root: str,
    **kwargs: Any,
) -> EvolutionTransaction:
    """Fail closed unless the requested mutations satisfy the Bucket 2 contract."""
    validate_work_capability(capability)
    capability.authorize(mutations)
    domains = tuple(getattr(spec.mutation, "domain", "") for spec in (*repair_specs, *dependent_specs))
    validate_mutation_domains(capability, domains)
    return execute_evolution_transaction(
        source=source,
        source_member=source_member,
        genome=genome,
        repair_specs=repair_specs,
        dependent_specs=dependent_specs,
        dependency_graph=dependency_graph,
        verifiers=verifiers,
        observations=observations,
        evidence_by_property=evidence_by_property,
        objectives=objectives,
        measurement_runners=measurement_runners,
        measurement_context=measurement_context,
        event_id=event_id,
        successor_architecture_id=successor_architecture_id,
        generation=generation,
        verification_config=verification_config,
        verification_root=verification_root,
        **kwargs,
    )
