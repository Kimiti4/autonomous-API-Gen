"""Executable verification plans for specialized engineering mutations."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Callable, Mapping, Any
from .specialized_mutations import EngineeringMutationSpec


Verifier = Callable[[Mapping[str, Any]], bool]


@dataclass(frozen=True)
class VerificationGate:
    gate_id: str
    property_name: str
    verifier: Verifier
    required: bool = True


@dataclass(frozen=True)
class VerificationPlan:
    mutation_id: str
    domain: str
    risk_class: str
    gates: tuple[VerificationGate, ...]


@dataclass(frozen=True)
class GateResult:
    gate_id: str
    property_name: str
    passed: bool
    evidence: tuple[str, ...]


@dataclass(frozen=True)
class VerificationReport:
    mutation_id: str
    results: tuple[GateResult, ...]
    passed: bool


def build_verification_plan(
    spec: EngineeringMutationSpec,
    verifiers: Mapping[str, Verifier],
) -> VerificationPlan:
    missing = [
        p for p in spec.verification_properties
        if p not in verifiers
    ]
    if missing:
        raise ValueError("missing-verifiers:" + ",".join(missing))
    gates = tuple(
        VerificationGate(
            f"{spec.mutation.request.domain}:{p}",
            p,
            verifiers[p],
        )
        for p in spec.verification_properties
    )
    return VerificationPlan(
        spec.mutation.mutation_id,
        spec.mutation.request.domain,
        spec.risk_class,
        gates,
    )


def execute_verification(
    plan: VerificationPlan,
    observations: Mapping[str, Any],
    evidence_by_gate: Mapping[str, tuple[str, ...]],
) -> VerificationReport:
    results = []
    for gate in plan.gates:
        evidence = evidence_by_gate.get(gate.gate_id, ())
        if gate.required and not evidence:
            raise ValueError(f"missing-evidence:{gate.gate_id}")
        passed = bool(gate.verifier(observations))
        results.append(
            GateResult(gate.gate_id, gate.property_name, passed, evidence)
        )
    report_results = tuple(results)
    return VerificationReport(
        plan.mutation_id,
        report_results,
        all(r.passed for r in report_results),
    )


def require_verification_pass(report: VerificationReport) -> None:
    if not report.passed:
        failed = ",".join(r.gate_id for r in report.results if not r.passed)
        raise ValueError("verification-failed:" + failed)
