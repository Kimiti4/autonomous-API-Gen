"""Execute materialized co-evolution work through mutation, verification, and event closure."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Any

from .architecture_mutation import execute_mutation
from .cross_domain_evolution import (
    CoEvolutionEvent,
    CoEvolutionResult,
    complete_coevolution,
    create_coevolution_event,
)
from .evolution_population import EvolutionMember
from .fullstack_genome import FullStackGenome
from .materialize_coevolution import ExecutableCoEvolutionWork
from .specialized_mutations import EngineeringMutationSpec
from .verification_plans import (
    VerificationReport,
    build_verification_plan,
    execute_verification,
)
from .transaction_verification import CandidateVerification, TransactionVerificationConfig, execute_transaction_verification
from .verification_command_planner import VerificationCommandRule
from .work_scope_verification import derive_work_verification_plan


@dataclass(frozen=True)
class DomainExecution:
    domain: str
    mutation_id: str
    candidate: FullStackGenome
    verification: VerificationReport


@dataclass(frozen=True)
class ExecutableCoEvolutionResult:
    event: CoEvolutionEvent
    candidate_architecture_id: str
    domain_executions: tuple[DomainExecution, ...]
    result: CoEvolutionResult
    executable_verification: CandidateVerification | None = None


def execute_materialized_coevolution(
    work: ExecutableCoEvolutionWork,
    source: EvolutionMember,
    genome: FullStackGenome,
    mutation_specs: tuple[EngineeringMutationSpec, ...],
    verifiers: Mapping[str, Any],
    observations: Mapping[str, Any],
    evidence_by_property: Mapping[str, tuple[str, ...]],
    *,
    event_id: str,
    candidate_architecture_id: str | None = None,
    contracts_by_domain: Mapping[str, tuple[Any, ...]] | None = None,
    verification_command_rules: tuple[VerificationCommandRule, ...] = (),
    verification_root: str | None = None,
    verification_workspace_id: str | None = None,
) -> ExecutableCoEvolutionResult:
    """Turn materialized domain work into candidates, verification reports, and a closed event.

    Execution is fail-closed: uncertain impact plans cannot be executed, every
    planned mutation must be present, every verification property must have a
    verifier and evidence, and every domain must yield a verification report.
    Mutations are applied sequentially so each domain observes the candidate
    produced by the previous domain.
    """
    if work.uncertain:
        raise ValueError("cannot-execute-uncertain-coevolution-work")
    if not work.work:
        raise ValueError("coevolution-work-requires-domain-items")

    specs_by_id = {s.mutation.mutation_id: s for s in mutation_specs}
    ordered_specs: list[EngineeringMutationSpec] = []
    for item in work.work:
        spec = specs_by_id.get(item.mutation_id)
        if spec is None:
            raise ValueError("missing-materialized-mutation:" + item.mutation_id)
        if spec.mutation.request.domain != item.domain:
            raise ValueError("materialized-domain-mismatch:" + item.mutation_id)
        if tuple(spec.verification_properties) != tuple(item.required_properties):
            raise ValueError("materialized-verification-contract-mismatch:" + item.mutation_id)
        ordered_specs.append(spec)

    current = genome
    executions: list[DomainExecution] = []
    reports: list[VerificationReport] = []
    combined_evidence = set(work.evidence)

    for item, spec in zip(work.work, ordered_specs):
        contracts = () if contracts_by_domain is None else contracts_by_domain.get(item.domain, ())
        mutation_evaluation = execute_mutation(
            current,
            spec.mutation,
            tuple(contracts),
            dict(observations),
        )
        current = mutation_evaluation.genome

        plan = build_verification_plan(spec, verifiers)
        evidence_by_gate = {}
        for property_name in spec.verification_properties:
            evidence = tuple(evidence_by_property.get(property_name, ()))
            if not evidence:
                raise ValueError("missing-verification-evidence:" + item.domain + ":" + property_name)
            evidence_by_gate[f"{item.domain}:{property_name}"] = evidence
            combined_evidence.update(evidence)

        report = execute_verification(plan, observations, evidence_by_gate)
        reports.append(report)
        combined_evidence.update(mutation_evaluation.evidence)
        executions.append(
            DomainExecution(item.domain, item.mutation_id, current, report)
        )

    event = create_coevolution_event(
        event_id,
        source,
        tuple(ordered_specs),
        tuple(sorted(combined_evidence)),
    )
    child_id = candidate_architecture_id or f"{source.lineage.architecture_id}:{event_id}"
    result = complete_coevolution(event, child_id, tuple(reports))

    executable_verification = None
    configured = bool(verification_command_rules) or verification_root is not None or verification_workspace_id is not None
    if configured:
        if not verification_command_rules or verification_root is None or verification_workspace_id is None:
            raise ValueError("incomplete-work-verification-configuration")
        work_plan = derive_work_verification_plan(
            (item.domain for item in work.work),
            workspace_id=verification_workspace_id,
            command_rules=verification_command_rules,
        )
        executable_verification = execute_transaction_verification(
            TransactionVerificationConfig(
                specs=work_plan.executable.specs,
                policies=work_plan.executable.policies,
                acceptance=work_plan.obligations.acceptance,
                expected_artifacts={},
            ),
            root=verification_root,
        )

    return ExecutableCoEvolutionResult(
        event,
        child_id,
        tuple(executions),
        result,
        executable_verification,
    )
