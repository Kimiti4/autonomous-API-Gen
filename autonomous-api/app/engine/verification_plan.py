"""Turn adversarial findings into executable, traceable verification plans."""
from __future__ import annotations
from dataclasses import dataclass
from .adversarial_review import CorrectionReview


@dataclass(frozen=True)
class VerificationObligation:
    obligation_id: str
    correction_id: str
    category: str
    statement: str
    required_evidence: tuple[str, ...]
    status: str = "unverified"


@dataclass(frozen=True)
class VerificationPlan:
    correction_id: str
    obligations: tuple[VerificationObligation, ...]
    disposition: str


def build_verification_plan(review: CorrectionReview) -> VerificationPlan:
    obligations = tuple(
        VerificationObligation(
            f"{finding.finding_id}:verify",
            review.correction_id,
            finding.category,
            finding.verification_obligation,
            ("execution-result", "test-output", "trace-or-metric"),
        )
        for finding in review.findings
    )
    return VerificationPlan(
        review.correction_id,
        obligations,
        "requires-evidence" if obligations else "no-derived-obligations",
    )


def record_verification(
    plan: VerificationPlan,
    results: dict[str, bool],
) -> VerificationPlan:
    updated = tuple(
        VerificationObligation(
            o.obligation_id,
            o.correction_id,
            o.category,
            o.statement,
            o.required_evidence,
            "pass" if results.get(o.obligation_id) is True
            else "fail" if results.get(o.obligation_id) is False
            else "unverified",
        )
        for o in plan.obligations
    )
    if any(o.status == "fail" for o in updated):
        disposition = "failed"
    elif updated and all(o.status == "pass" for o in updated):
        disposition = "evidence-complete"
    else:
        disposition = "partially-verified"
    return VerificationPlan(plan.correction_id, updated, disposition)


def is_eligible_for_evolution(plan: VerificationPlan) -> bool:
    return bool(plan.obligations) and plan.disposition == "evidence-complete"
