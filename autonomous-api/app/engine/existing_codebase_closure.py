"""Bucket 4.1 final closure gate for existing-codebase work.

The gate only decides whether the authorized maintenance/improvement objective
has enough evidence to stop. It does not mutate, deploy, or invent work.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from hashlib import sha256

from .existing_codebase_audit import ExistingCodebaseAudit
from .project_completion import CompletionState


class ClosureDecision(str, Enum):
    CONTINUE = "continue"
    STOP = "stop"
    REJECT = "reject"


@dataclass(frozen=True)
class ExistingCodebaseClosure:
    decision: ClosureDecision
    reasons: tuple[str, ...]
    digest: str

    @property
    def stopped(self) -> bool:
        return self.decision is ClosureDecision.STOP


def close_existing_codebase_work(
    audit: ExistingCodebaseAudit,
    completion: CompletionState,
    *,
    verification_complete: bool,
    documentation_complete: bool,
    deployment_ready: bool,
) -> ExistingCodebaseClosure:
    reasons: list[str] = []

    if not audit.audit_decision.may_claim_full_audit:
        reasons.append("repository-audit-incomplete")
    if not audit.audit_decision.may_certify_repair:
        reasons.append("repair-certification-evidence-incomplete")
    if not completion.complete:
        reasons.append("authoritative-obligations-incomplete")
    if not verification_complete:
        reasons.append("verification-incomplete")
    if not documentation_complete:
        reasons.append("documentation-incomplete")
    if not deployment_ready:
        reasons.append("deployment-readiness-incomplete")

    decision = ClosureDecision.STOP if not reasons else ClosureDecision.CONTINUE
    canonical = "|".join((
        decision.value,
        completion.state_digest,
        audit.digest,
        str(verification_complete),
        str(documentation_complete),
        str(deployment_ready),
        *sorted(reasons),
    ))
    return ExistingCodebaseClosure(
        decision=decision,
        reasons=tuple(sorted(reasons)),
        digest=sha256(canonical.encode())  # nosec B324.hexdigest(),
    )
