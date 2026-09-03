"""Governed backend-swap evolution policy (D4).

Decides whether a failed trial may spawn an evolved candidate, and which
alternate backend.  The decision is AUDITABLE (returns a structured reason).

Critical epistemic rules:
  - Infrastructure failures NEVER trigger backend evolution (a rust registry
    outage must not teach "rust is bad").
  - The alternate must be an eligible behavioral backend that supports the
    workload, differs from the failed backend, and was not already attempted
    for this parent.
  - Backend selection comes from the registry/eligibility mechanism, never a
    hardcoded rust→python mapping.
"""
from __future__ import annotations

from dataclasses import dataclass

from certification.feedback.rule import (
    FailureClassification,
    DOMAIN_INFRASTRUCTURE,
    DOMAIN_PROVENANCE,
)
from certification.feedback.candidate import EvolutionCandidate


@dataclass(frozen=True)
class EvolutionDecision:
    accepted: bool
    reason: str
    alternate_backend_id: str | None = None

    def as_record(self) -> dict:
        return {
            "accepted": self.accepted,
            "reason": self.reason,
            "alternate_backend_id": self.alternate_backend_id,
        }


# Domains that forbid backend evolution (LEARN ONLY).
_NO_EVOLVE_DOMAINS = frozenset({
    DOMAIN_INFRASTRUCTURE,
    DOMAIN_PROVENANCE,
})


class BackendSwapPolicy:
    """Auditable gate for backend-variant evolution."""

    def should_evolve(
        self,
        *,
        classification: FailureClassification,
        failed_backend_id: str,
        eligible_backend_ids: list[str],
        attempted_backend_ids: frozenset[str] | set[str] = frozenset(),
        supports_workload: set[str] | frozenset[str] | None = None,
    ) -> EvolutionDecision:
        """Return whether an evolved backend candidate is justified, and which
        alternate backend to use."""
        if not classification.repair_eligible:
            return EvolutionDecision(
                accepted=False,
                reason=(
                    f"not repair-eligible (domain={classification.feedback_domain}, "
                    f"cause={classification.cause})"
                ),
            )
        if classification.feedback_domain in _NO_EVOLVE_DOMAINS:
            return EvolutionDecision(
                accepted=False,
                reason=(
                    f"domain={classification.feedback_domain} is LEARN-ONLY; "
                    "infrastructure/provenance failures do not justify workload "
                    "evolution"
                ),
            )

        tried = set(attempted_backend_ids)
        tried.add(failed_backend_id)

        candidates = [b for b in eligible_backend_ids if b not in tried]
        if supports_workload is not None:
            candidates = [b for b in candidates if b in supports_workload]

        if not candidates:
            return EvolutionDecision(
                accepted=False,
                reason=(
                    "no alternate eligible behavioral backend supports this "
                    "workload besides the failed/attempted one(s)"
                ),
            )

        alternate = candidates[0]
        return EvolutionDecision(
            accepted=True,
            reason=(
                f"behavioral failure with alternate eligible backend "
                f"{alternate} (failed={failed_backend_id})"
            ),
            alternate_backend_id=alternate,
        )


def make_candidate(
    *,
    decision: EvolutionDecision,
    parent_trial_id: str,
    intent_id: str,
    isr_hash: str,
    genome_hash: str,
    reason: str = "",
    parent_candidate_id: str | None = None,
    parent_backend_id: str = "",
) -> EvolutionCandidate | None:
    """Materialize a candidate only when the policy accepted the evolution."""
    if not decision.accepted or not decision.alternate_backend_id:
        return None
    return EvolutionCandidate(
        parent_trial_id=parent_trial_id,
        intent_id=intent_id,
        isr_hash=isr_hash,
        genome_hash=genome_hash,
        backend_id=decision.alternate_backend_id,
        reason=reason or decision.reason,
        parent_candidate_id=parent_candidate_id,
        parent_backend_id=parent_backend_id,
    )


class BackendSwapStrategy:
    """The D5 operator: policy → candidate for backend-variant self-repair.

    Decouples "should we and which backend?" (BackendSwapPolicy) from the
    submission/execution concern.  Kept pure (no I/O, no ledger writes) so
    it stays auditable and testable; the caller drives novelty/materialization
    via `certification.feedback.execution`.
    """

    def __init__(self, policy: BackendSwapPolicy | None = None) -> None:
        self.policy = policy or BackendSwapPolicy()

    def propose(
        self,
        *,
        classification: FailureClassification,
        parent_trial_id: str,
        intent_id: str,
        isr_hash: str,
        genome_hash: str,
        failed_backend_id: str,
        eligible_backend_ids: list[str],
        attempted_backend_ids: frozenset[str] | set[str] = frozenset(),
        supports_workload: set[str] | frozenset[str] | None = None,
        reason: str = "",
        parent_candidate_id: str | None = None,
    ) -> tuple[EvolutionDecision, EvolutionCandidate | None]:
        """Return (decision, candidate) — candidate only when accepted."""
        decision = self.policy.should_evolve(
            classification=classification,
            failed_backend_id=failed_backend_id,
            eligible_backend_ids=eligible_backend_ids,
            attempted_backend_ids=attempted_backend_ids,
            supports_workload=supports_workload,
        )
        candidate = make_candidate(
            decision=decision,
            parent_trial_id=parent_trial_id,
            intent_id=intent_id,
            isr_hash=isr_hash,
            genome_hash=genome_hash,
            reason=reason,
            parent_candidate_id=parent_candidate_id,
            parent_backend_id=failed_backend_id,
        )
        return decision, candidate
