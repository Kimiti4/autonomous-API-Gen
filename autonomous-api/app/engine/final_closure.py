"""Final ESAP completion/stop gate.

A work item may stop only when its authoritative obligations are complete,
required verification evidence is complete, and every required deployment step
is ready. Advisory findings remain visible but never become new requirements.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import hashlib
import json
from typing import Iterable


class ClosureStatus(str, Enum):
    READY_TO_STOP = "READY_TO_STOP"
    BLOCKED = "BLOCKED"


@dataclass(frozen=True)
class FinalClosureAssessment:
    work_id: str
    status: ClosureStatus
    authorized_obligation_ids: tuple[str, ...]
    completed_obligation_ids: tuple[str, ...]
    missing_obligation_ids: tuple[str, ...]
    verification_evidence_complete: bool
    deployment_required: bool
    deployment_ready: bool
    blocking_findings: tuple[str, ...]
    advisory_findings: tuple[str, ...]
    digest: str

    @property
    def ready_to_stop(self) -> bool:
        return self.status is ClosureStatus.READY_TO_STOP

    @property
    def all_authoritative_obligations_complete(self) -> bool:
        return not self.missing_obligation_ids

    def canonical_payload(self) -> dict[str, object]:
        return {
            "work_id": self.work_id,
            "status": self.status.value,
            "authorized_obligation_ids": list(self.authorized_obligation_ids),
            "completed_obligation_ids": list(self.completed_obligation_ids),
            "missing_obligation_ids": list(self.missing_obligation_ids),
            "verification_evidence_complete": self.verification_evidence_complete,
            "deployment_required": self.deployment_required,
            "deployment_ready": self.deployment_ready,
            "blocking_findings": list(self.blocking_findings),
            "advisory_findings": list(self.advisory_findings),
        }


def assess_final_closure(
    *,
    work_id: str,
    authorized_obligation_ids: Iterable[str],
    completed_obligation_ids: Iterable[str],
    verification_evidence_complete: bool,
    deployment_required: bool = False,
    deployment_ready: bool = True,
    blocking_findings: Iterable[str] = (),
    advisory_findings: Iterable[str] = (),
) -> FinalClosureAssessment:
    if not work_id:
        raise ValueError("closure-missing-work-id")

    authorized = tuple(sorted(set(authorized_obligation_ids)))
    completed = tuple(sorted(set(completed_obligation_ids)))
    blocking = tuple(sorted(set(f for f in blocking_findings if f)))
    advisory = tuple(sorted(set(f for f in advisory_findings if f)))

    if not authorized:
        raise ValueError("closure-missing-authoritative-obligations")

    missing = tuple(sorted(set(authorized) - set(completed)))
    reasons: list[str] = []
    if missing:
        reasons.append("authoritative-obligations-incomplete")
    if not verification_evidence_complete:
        reasons.append("verification-evidence-incomplete")
    if deployment_required and not deployment_ready:
        reasons.append("deployment-not-ready")
    if blocking:
        reasons.append("blocking-findings-present")

    status = ClosureStatus.READY_TO_STOP if not reasons else ClosureStatus.BLOCKED
    assessment = FinalClosureAssessment(
        work_id=work_id,
        status=status,
        authorized_obligation_ids=authorized,
        completed_obligation_ids=completed,
        missing_obligation_ids=missing,
        verification_evidence_complete=verification_evidence_complete,
        deployment_required=deployment_required,
        deployment_ready=deployment_ready,
        blocking_findings=blocking,
        advisory_findings=advisory,
        digest="",
    )
    digest = hashlib.sha256(
        json.dumps(assessment.canonical_payload(), sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    return FinalClosureAssessment(**{**assessment.__dict__, "digest": digest})


def require_final_closure(assessment: FinalClosureAssessment) -> None:
    if not assessment.ready_to_stop:
        raise ValueError(
            "closure-not-ready-to-stop:" + (
                "authoritative-obligations-incomplete"
                if assessment.missing_obligation_ids
                else "verification-or-deployment-or-blocking-findings"
            )
        )
    if assessment.digest != hashlib.sha256(
        json.dumps(assessment.canonical_payload(), sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest():
        raise ValueError("closure-digest-invalid")
