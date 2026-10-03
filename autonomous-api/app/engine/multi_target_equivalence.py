"""Multi-target behavioral and invariant equivalence model."""
from __future__ import annotations
from dataclasses import dataclass
from .verification_artifacts import VerificationExecution
from .verification_obligations import VerificationObligation


@dataclass(frozen=True)
class EquivalenceClaim:
    claim_id: str
    obligation_id: str
    required_invariants: tuple[str, ...]
    allowed_target_differences: tuple[str, ...] = ()


@dataclass(frozen=True)
class TargetResult:
    target: str
    obligation_id: str
    status: str
    observed_behavior: str
    invariants: tuple[str, ...]
    evidence_id: str = ""


@dataclass(frozen=True)
class EquivalenceVerdict:
    claim_id: str
    verdict: str
    targets: tuple[str, ...]
    reason: str


def derive_equivalence_claim(
    obligation: VerificationObligation,
    required_invariants: tuple[str, ...],
    claim_id: str | None = None,
) -> EquivalenceClaim:
    return EquivalenceClaim(
        claim_id or f"EQUIV-{obligation.obligation_id}",
        obligation.obligation_id,
        required_invariants,
    )


def verify_target_equivalence(
    claim: EquivalenceClaim,
    results: tuple[TargetResult, ...],
) -> EquivalenceVerdict:
    matching = tuple(r for r in results if r.obligation_id == claim.obligation_id)
    if len(matching) < 2:
        return EquivalenceVerdict(claim.claim_id, "INCONCLUSIVE", tuple(r.target for r in matching),
                                  "at least two target results are required")
    if any(r.status != "passed" for r in matching):
        return EquivalenceVerdict(claim.claim_id, "FAIL", tuple(r.target for r in matching),
                                  "one or more targets did not pass")
    required = set(claim.required_invariants)
    missing = {
        r.target: sorted(required - set(r.invariants))
        for r in matching
        if required - set(r.invariants)
    }
    if missing:
        return EquivalenceVerdict(claim.claim_id, "FAIL", tuple(r.target for r in matching),
                                  f"required invariants missing: {missing}")
    behaviors = {r.observed_behavior for r in matching}
    if len(behaviors) > 1:
        return EquivalenceVerdict(claim.claim_id, "INCONCLUSIVE", tuple(r.target for r in matching),
                                  "observable behavior differs; target-specific difference requires review")
    return EquivalenceVerdict(claim.claim_id, "PASS", tuple(r.target for r in matching),
                              "all targets satisfy required invariants and observed behavior")


def target_result_from_execution(
    target: str,
    obligation_id: str,
    execution: VerificationExecution,
    observed_behavior: str,
    invariants: tuple[str, ...],
    evidence_id: str = "",
) -> TargetResult:
    return TargetResult(target, obligation_id, execution.status, observed_behavior, invariants, evidence_id)
