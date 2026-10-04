"""Bridge executable verification failures into the existing ESAP repair engine."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Mapping, Any

from .fullstack_genome import FullStackGenome
from .repair_coevolution import RepairCandidate, RepairExecution
from .verification_failure_repair import VerificationRepairRequest
from .architecture_mutation import execute_mutation
from .specialized_mutations import EngineeringMutationSpec
from .verification_plans import build_verification_plan, execute_verification


@dataclass(frozen=True)
class EngineRepairResult:
    architecture: FullStackGenome
    execution: RepairExecution | None


def execute_verification_repair(
    request: VerificationRepairRequest,
    *,
    genome: FullStackGenome,
    repair_specs: Mapping[str, EngineeringMutationSpec],
    observations: Mapping[str, Any],
    contracts_by_domain: Mapping[str, tuple[Any, ...]] | None,
    verifiers: Mapping[str, Any],
    evidence_by_property: Mapping[str, tuple[str, ...]],
) -> EngineRepairResult:
    candidate = request.candidate
    if candidate is None:
        raise ValueError("missing-verification-repair-mutation")
    spec = repair_specs.get(candidate.repair_mutation_id)
    if spec is None:
        raise ValueError("missing-repair-spec:" + candidate.repair_mutation_id)
    contracts = () if contracts_by_domain is None else contracts_by_domain.get(candidate.domain, ())
    evaluation = execute_mutation(genome, spec.mutation, tuple(contracts), dict(observations))
    plan = build_verification_plan(spec, verifiers)
    evidence_by_gate = {
        f"{candidate.domain}:{p}": tuple(evidence_by_property.get(p, ()))
        for p in spec.verification_properties
    }
    report = execute_verification(plan, observations, evidence_by_gate)
    execution = RepairExecution(candidate, evaluation.genome, report)
    if not report.passed:
        raise ValueError("repair-verification-failed:" + candidate.domain)
    return EngineRepairResult(evaluation.genome, execution)
