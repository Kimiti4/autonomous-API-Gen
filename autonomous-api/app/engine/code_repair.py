"""Governed bug/jagged-code repair planning for repository scans.

Scanning is read-only. Repairs require an explicit mutation specification and
must be re-verified through the existing ESAP verification machinery.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Any

from .architecture_mutation import execute_mutation
from .fullstack_genome import FullStackGenome
from .repository_code_scan import CodeFinding, RepositoryScan
from .specialized_mutations import EngineeringMutationSpec
from .verification_plans import build_verification_plan, execute_verification


@dataclass(frozen=True)
class CodeRepairPlan:
    finding_id: str
    mutation_id: str
    domain: str
    rationale: str


@dataclass(frozen=True)
class CodeRepairResult:
    finding_id: str
    mutation_id: str
    architecture: FullStackGenome
    passed: bool
    verification_evidence: tuple[str, ...]


def plan_code_repairs(
    scan: RepositoryScan,
    specs_by_finding: Mapping[str, EngineeringMutationSpec],
) -> tuple[CodeRepairPlan, ...]:
    plans = []
    for finding in scan.findings:
        if not finding.repairable:
            continue
        spec = specs_by_finding.get(finding.finding_id)
        if spec is None:
            # Never invent a repair operator for an observed defect.
            continue
        plans.append(CodeRepairPlan(
            finding.finding_id,
            spec.mutation.mutation_id,
            spec.mutation.request.domain,
            spec.mutation.request.rationale,
        ))
    return tuple(plans)


def execute_code_repair(
    finding: CodeFinding,
    spec: EngineeringMutationSpec,
    *,
    genome: FullStackGenome,
    contracts: tuple[Any, ...],
    observations: Mapping[str, Any],
    verifiers: Mapping[str, Any],
    evidence_by_property: Mapping[str, tuple[str, ...]],
) -> CodeRepairResult:
    if finding.finding_id == "":
        raise ValueError("missing-code-finding-id")
    evaluation = execute_mutation(genome, spec.mutation, contracts, dict(observations))
    plan = build_verification_plan(spec, verifiers)
    evidence = {
        f"{spec.mutation.request.domain}:{p}": tuple(evidence_by_property.get(p, ()))
        for p in spec.verification_properties
    }
    report = execute_verification(plan, observations, evidence)
    if not report.passed:
        raise ValueError(f"code-repair-verification-failed:{finding.finding_id}")
    return CodeRepairResult(
        finding.finding_id,
        spec.mutation.mutation_id,
        evaluation.genome,
        True,
        tuple(sorted({e for r in report.results for e in r.evidence})),
    )
