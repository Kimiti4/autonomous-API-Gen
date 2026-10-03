"""Execute one bounded end-to-end co-evolution transaction."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Mapping, Sequence
from .cross_domain_evolution import CoEvolutionResult
from .dependency_reexecution import DependencyExecutionResult, execute_dependent_reverification
from .evidence_scoring import DerivedArchitectureScore, derive_architecture_score
from .candidate_measurements import CandidateMeasurementResult, execute_candidate_measurements, measurement_evidence_map
from .repair_coevolution import execute_repairs
from .successor_admission import SuccessorAdmission, SuccessorEvent, admit_successor, materialize_successor_event
from .evolution_population import EvolutionMember
from .pareto_architecture import Objective
from .specialized_mutations import EngineeringMutationSpec
from .fullstack_genome import FullStackGenome
from .transaction_evidence import TransactionEvidenceRecord, materialize_transaction_evidence


@dataclass(frozen=True)
class EvolutionTransaction:
    source_event_id: str
    source_architecture_id: str
    dependency_execution: DependencyExecutionResult
    measurements: CandidateMeasurementResult
    derived_score: DerivedArchitectureScore
    successor: SuccessorEvent
    admission: SuccessorAdmission
    audit_record: TransactionEvidenceRecord


def execute_evolution_transaction(
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
    *,
    event_id: str,
    successor_architecture_id: str,
    generation: int,
    contracts_by_domain: Mapping[str, tuple[Any, ...]] | None = None,
    parent_evidence_digest: str | None = None,
) -> EvolutionTransaction:
    repairs_result = execute_repairs(
        source, source_member, genome, repair_specs, verifiers, observations,
        evidence_by_property, contracts_by_domain=contracts_by_domain,
    )

    dependency_result = execute_dependent_reverification(
        source,
        repairs_result.repairs,
        dependency_graph,
        dependent_specs,
        verifiers,
        observations,
        evidence_by_property,
        successor_architecture_id=successor_architecture_id,
    )

    if dependency_result.final_architecture is None:
        raise ValueError("transaction-missing-final-architecture")

    measurements = execute_candidate_measurements(
        successor_architecture_id,
        dependency_result.final_architecture,
        objectives,
        measurement_runners,
        measurement_context,
    )

    score = derive_architecture_score(
        successor_architecture_id,
        repairs_result.repairs,
        dependency_result,
        objectives,
        measurement_evidence=measurement_evidence_map(measurements),
    )

    successor = materialize_successor_event(
        source,
        dependency_result,
        event_id=event_id,
        source_member=source_member,
        score=score.score,
    )
    admission = admit_successor(
        source_member,
        successor,
        score.score,
        objectives,
        generation,
    )
    audit_record = materialize_transaction_evidence(
        transaction_id=event_id,
        source_event_id=source.event.event_id,
        source_architecture_id=source.architecture_id,
        successor=successor,
        repairs=repairs_result.repairs,
        dependency=dependency_result,
        measurements=measurements,
        score=score,
        admission=admission,
        parent_digest=parent_evidence_digest,
    )

    return EvolutionTransaction(
        source.event.event_id,
        source.architecture_id,
        dependency_result,
        measurements,
        score,
        successor,
        admission,
        audit_record,
    )
