"""Production certification bridge for generated full-stack applications.

Compilation is necessary but never sufficient. This adapter makes the
full-stack hardening contract the certification boundary: missing, UNKNOWN,
NOT_APPLICABLE, or FAIL gates cannot certify an application.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Mapping

from tiannara.application.hardening.fullstack_gates import (
    FULLSTACK_HARDENING_GATES,
    GateResult,
    GateStatus,
    certify_hardening,
)


@dataclass(frozen=True)
class HardeningCertificationResult:
    certified: bool
    blockers: tuple[str, ...]
    gate_results: tuple[GateResult, ...]


def evaluate_hardening_certification(
    results: Iterable[GateResult],
) -> HardeningCertificationResult:
    observed = {result.gate_id: result for result in results}
    normalized: list[GateResult] = []
    blockers: list[str] = []

    for gate in FULLSTACK_HARDENING_GATES:
        result = observed.get(gate.gate_id)
        if result is None:
            result = GateResult(gate.gate_id, GateStatus.UNKNOWN, (), "gate result absent")
        normalized.append(result)
        if result.status is not GateStatus.PASS:
            blockers.append(f"{gate.gate_id}:{result.status.value}")

    certified = certify_hardening(normalized) and not blockers
    return HardeningCertificationResult(
        certified=certified,
        blockers=tuple(blockers),
        gate_results=tuple(normalized),
    )


def certify_generated_application(
    *,
    compilation_ok: bool,
    gate_results: Iterable[GateResult],
) -> HardeningCertificationResult:
    """Certification boundary used after generation and execution evidence.

    A successful compiler run alone cannot certify an application. The
    complete hardening contract must independently resolve to PASS.
    """
    result = evaluate_hardening_certification(gate_results)
    if not compilation_ok:
        return HardeningCertificationResult(
            certified=False,
            blockers=("COMPILATION:fail", *result.blockers),
            gate_results=result.gate_results,
        )
    return result
