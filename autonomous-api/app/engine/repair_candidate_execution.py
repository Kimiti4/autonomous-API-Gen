"""Execute bounded repository repair candidates and produce selector evaluations."""

from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Mapping, Sequence

from .architecture_mutation import execute_mutation
from .repository_root_cause import RepairCandidate
from .repair_candidate_selection import CandidateEvaluation, RepairSelection, select_verified_repair
from .verification_plans import build_verification_plan, execute_verification

@dataclass(frozen=True)
class CandidateExecutionContext:
    genome: Any
    contracts: tuple[Any, ...]
    observations: Mapping[str, Any]
    specs_by_candidate: Mapping[str, Any]
    verifiers: Mapping[str, Any]
    evidence_by_property: Mapping[str, tuple[str, ...]]
    regression_checker: Any
    measurement_runner: Any

def execute_repair_candidates(
    candidates: Sequence[RepairCandidate],
    *,
    context: CandidateExecutionContext,
) -> RepairSelection:
    evaluations=[]
    for candidate in candidates:
        spec=context.specs_by_candidate.get(candidate.candidate_id)
        if spec is None:
            evaluations.append(CandidateEvaluation(
                candidate.candidate_id,False,0.0,False,0.0,(),
                ("missing-repair-spec",)))
            continue
        try:
            evaluation=execute_mutation(
                context.genome, spec.mutation, context.contracts,
                dict(context.observations),
            )
            plan=build_verification_plan(spec, context.verifiers)
            evidence={
                f"{spec.mutation.request.domain}:{p}":
                tuple(context.evidence_by_property.get(p, ()))
                for p in spec.verification_properties
            }
            report=execute_verification(plan, context.observations, evidence)
            if not report.passed:
                evaluations.append(CandidateEvaluation(
                    candidate.candidate_id,False,0.0,False,0.0,
                    tuple(sorted({x for r in report.results for x in r.evidence})),
                    ("verification-failed",)))
                continue
            regression_free=bool(context.regression_checker(evaluation.genome))
            measurement=float(context.measurement_runner(evaluation.genome))
            score=sum(1.0 for r in report.results if r.passed)/max(1,len(report.results))
            evaluations.append(CandidateEvaluation(
                candidate.candidate_id,True,score,regression_free,measurement,
                tuple(sorted({x for r in report.results for x in r.evidence})),
                () if regression_free else ("regression-detected",),
            ))
        except Exception as exc:
            evaluations.append(CandidateEvaluation(
                candidate.candidate_id,False,0.0,False,0.0,(),
                (f"candidate-execution-failed:{type(exc).__name__}",)))
    return select_verified_repair(candidates,evaluations)
