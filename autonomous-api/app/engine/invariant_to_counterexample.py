"""Bridge invariant violations into counterexample-guided evolution."""
from __future__ import annotations
from dataclasses import dataclass
from .invariant_contracts import InvariantResult
from .counterexample_guidance import Counterexample, MutationHypothesis, infer_mutation_hypothesis


@dataclass(frozen=True)
class InvariantCounterexample:
    counterexample: Counterexample
    invariant_id: str
    domain: str
    violation_evidence: tuple[str, ...]


@dataclass(frozen=True)
class RepairCase:
    counterexample: InvariantCounterexample
    hypothesis: MutationHypothesis
    regression_properties: tuple[str, ...]


def invariant_violation_to_counterexample(
    result: InvariantResult,
    domain: str,
    observations: dict[str, object] | None = None,
) -> InvariantCounterexample:
    if result.passed:
        raise ValueError("passed-invariant-is-not-counterexample")
    evidence = tuple(result.evidence)
    if not evidence:
        raise ValueError("counterexample-requires-evidence")
    cx = Counterexample(
        counterexample_id=f"inv:{result.invariant_id}",
        domain=domain,
        violated_property=result.invariant_id,
        evidence=evidence,
        observations=observations or {},
    )
    return InvariantCounterexample(cx, result.invariant_id, domain, evidence)


def create_repair_case(
    violation: InvariantCounterexample,
    regression_properties: tuple[str, ...] = (),
) -> RepairCase:
    return RepairCase(
        counterexample=violation,
        hypothesis=infer_mutation_hypothesis(violation.counterexample),
        regression_properties=regression_properties,
    )


def require_repair_target(case: RepairCase) -> tuple[str, ...]:
    targets = tuple(case.hypothesis.target_properties)
    if not targets:
        raise ValueError("repair-requires-target-property")
    return targets
