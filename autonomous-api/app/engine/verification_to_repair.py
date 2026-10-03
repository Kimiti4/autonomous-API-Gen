"""Bridge failed verification gates into evidence-backed repair candidates."""
from __future__ import annotations
from dataclasses import dataclass
from .verification_plans import VerificationReport, GateResult
from .counterexample_guidance import Counterexample, MutationHypothesis, infer_mutation_hypothesis


@dataclass(frozen=True)
class VerificationCounterexample:
    counterexample: Counterexample
    gate_id: str
    property_name: str


@dataclass(frozen=True)
class VerificationRepairCandidate:
    counterexample: VerificationCounterexample
    hypothesis: MutationHypothesis
    regression_gate_id: str


def failed_gates(report: VerificationReport) -> tuple[GateResult, ...]:
    return tuple(r for r in report.results if not r.passed)


def gate_to_counterexample(
    report: VerificationReport,
    gate: GateResult,
) -> VerificationCounterexample:
    if gate.passed:
        raise ValueError("passed-gate-is-not-counterexample")
    if gate not in report.results:
        raise ValueError("gate-not-in-report")
    if not gate.evidence:
        raise ValueError("counterexample-requires-evidence")
    cx = Counterexample(
        counterexample_id=f"verify:{report.mutation_id}:{gate.gate_id}",
        domain=gate.gate_id.split(":", 1)[0],
        violated_property=gate.property_name,
        evidence=gate.evidence,
        observations={},
    )
    return VerificationCounterexample(cx, gate.gate_id, gate.property_name)


def create_repair_candidate(
    report: VerificationReport,
    gate: GateResult,
) -> VerificationRepairCandidate:
    violation = gate_to_counterexample(report, gate)
    hypothesis = infer_mutation_hypothesis(violation.counterexample)
    return VerificationRepairCandidate(
        violation,
        hypothesis,
        gate.gate_id,
    )
