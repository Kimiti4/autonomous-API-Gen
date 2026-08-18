"""R2.10.9 — failure classification: the taxonomy that makes scale
diagnosable.

This is what turns Phase 31's success rate from a single number into an
understanding of WHERE and WHY generation fails. UNKNOWN is tolerated only
as a last resort — a campaign with many UNKNOWNs is a campaign whose
failures are not yet understood.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class FailureCategory(str, Enum):
    INTENT_DERIVATION_FAILED = "INTENT_DERIVATION_FAILED"
    EVOLUTION_HALTED = "EVOLUTION_HALTED"
    COMPILATION_FAILED = "COMPILATION_FAILED"
    COMPILATION_CONTRACT_VIOLATION = "COMPILATION_CONTRACT_VIOLATION"  # a gate failed
    VERIFICATION_FAILED = "VERIFICATION_FAILED"
    RESOURCE_EXHAUSTION = "RESOURCE_EXHAUSTION"
    TIMEOUT = "TIMEOUT"
    UNKNOWN = "UNKNOWN"


class ResourceExhaustionError(Exception):
    """The campaign exceeded its declared resource envelope."""


class CompilationContractViolation(Exception):
    """A frozen compilation gate failed (R2.10.6-7) — non-recoverable."""


class VerificationFailure(Exception):
    """The independent verifier (R2.10.8) could not complete a judgment."""


@dataclass(frozen=True)
class FailureClassification:
    category: FailureCategory
    stage: str  # which pipeline stage failed
    evidence: str  # the failure evidence
    recoverable: bool  # whether a retry could plausibly succeed


def classify_failure(error: Exception, stage: str) -> FailureClassification:
    """Classify a generation failure by its most specific known cause.

    Exceptions with a declared taxonomy win over stage heuristics; stage
    heuristics win over UNKNOWN. UNKNOWN is the last resort, never the
    default convenience.
    """
    if isinstance(error, ResourceExhaustionError):
        return FailureClassification(
            FailureCategory.RESOURCE_EXHAUSTION, stage, str(error), True
        )
    if isinstance(error, TimeoutError):
        return FailureClassification(
            FailureCategory.TIMEOUT, stage, str(error), True
        )
    if isinstance(error, CompilationContractViolation):
        return FailureClassification(
            FailureCategory.COMPILATION_CONTRACT_VIOLATION, stage, str(error), False
        )
    if isinstance(error, VerificationFailure):
        return FailureClassification(
            FailureCategory.VERIFICATION_FAILED, stage, str(error), False
        )
    if stage == "intent_derivation":
        return FailureClassification(
            FailureCategory.INTENT_DERIVATION_FAILED, stage, str(error), False
        )
    if stage == "evolution":
        return FailureClassification(
            FailureCategory.EVOLUTION_HALTED, stage, str(error), True
        )
    if stage == "compilation":
        return FailureClassification(
            FailureCategory.COMPILATION_FAILED, stage, str(error), True
        )
    return FailureClassification(
        FailureCategory.UNKNOWN, stage, str(error), False
    )