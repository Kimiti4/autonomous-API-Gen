"""Bounded executable-verification → repair → re-verification loop for ESAP."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Mapping, Sequence, Any

from .fullstack_genome import FullStackGenome
from .repair_coevolution import RepairCandidate
from .transaction_verification import CandidateVerification, TransactionVerificationConfig, execute_transaction_verification
from .verification_failure_repair import build_verification_repair_request


@dataclass(frozen=True)
class VerificationRepairIteration:
    attempt: int
    verification: CandidateVerification
    repair_request: Any | None


@dataclass(frozen=True)
class VerificationRepairLoopResult:
    final_verification: CandidateVerification
    iterations: tuple[VerificationRepairIteration, ...]
    repaired: bool


def execute_verification_repair_loop(
    initial: CandidateVerification,
    *,
    repair_executor: Any,
    verification_config: TransactionVerificationConfig,
    verification_root: str,
    repair_candidates: Mapping[str, RepairCandidate],
    max_attempts: int = 2,
) -> VerificationRepairLoopResult:
    if max_attempts < 1:
        raise ValueError("invalid-verification-repair-limit")
    current = initial
    iterations: list[VerificationRepairIteration] = []
    for attempt in range(1, max_attempts + 1):
        if current.disposition.disposition.value == "PASS":
            return VerificationRepairLoopResult(current, tuple(iterations), bool(iterations))
        request = build_verification_repair_request(
            current.results, repair_candidates=repair_candidates
        )
        repair_executor(request)
        current = execute_transaction_verification(
            verification_config, root=verification_root
        )
        iterations.append(VerificationRepairIteration(attempt, current, request))
    if current.disposition.disposition.value != "PASS":
        raise ValueError("verification-repair-limit-exhausted")
    return VerificationRepairLoopResult(current, tuple(iterations), True)
