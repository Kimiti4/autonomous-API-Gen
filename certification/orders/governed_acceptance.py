"""Orders governed acceptance — lifecycle + trusted evidence (Checkpoint 052)."""
from __future__ import annotations

from dataclasses import dataclass

from constitutional_architecture.governance.candidate_promotion_lifecycle import (
    CandidateLifecycleState,
    GovernedCandidatePromotionService,
)
from constitutional_architecture.governance.trusted_evidence_resolution import (
    GovernedTrustedEvidenceService,
    is_trusted_evidence_id,
)
from tiannara.application.engineering.senior_engineering_gate import (
    SeniorEngineeringAssessmentResult,
    SeniorEngineeringVerdict,
    evaluate_senior_engineering_acceptance,
)


@dataclass(frozen=True)
class OrdersGovernedAcceptanceResult:
    status: str
    candidate_state: str | None
    blockers: tuple[str, ...]
    lifecycle_verified: bool


def assess_orders_governed_acceptance(
    *,
    candidate_id: str,
    promotion: GovernedCandidatePromotionService | None,
    evidence: GovernedTrustedEvidenceService | None,
    runtime_evidence_id: str | None,
    durable_evidence_id: str | None,
    lifecycle_evidence_id: str | None,
    mandatory_full_stack_blockers: tuple[str, ...] = (),
) -> OrdersGovernedAcceptanceResult:
    blockers = list(mandatory_full_stack_blockers)
    candidate_state: str | None = None
    lifecycle_verified = False

    for label, ref in (
        ("runtime", runtime_evidence_id),
        ("durable-execution", durable_evidence_id),
        ("lifecycle", lifecycle_evidence_id),
    ):
        if not ref or not is_trusted_evidence_id(ref):
            blockers.append(f"orders-missing-trusted-{label}-evidence")

    if promotion is None or evidence is None:
        blockers.append("orders-governance-services-unconfigured")
    else:
        try:
            rec = promotion.get_candidate(candidate_id)
            candidate_state = rec.state.value
            if rec.state not in {
                CandidateLifecycleState.CERTIFIED,
                CandidateLifecycleState.PROMOTED,
            }:
                blockers.append(f"orders-candidate-not-certified:{rec.state.value}")
            ids = tuple(
                x
                for x in (
                    runtime_evidence_id,
                    durable_evidence_id,
                    lifecycle_evidence_id,
                )
                if x is not None
            )
            evidence.resolve_evidence(ids, binding=rec.binding(), require_runtime=True)
            lifecycle_verified = lifecycle_evidence_id is not None
        except ValueError as exc:
            blockers.append(str(exc))

    status = "ACCEPTANCE_BLOCKED" if blockers else "ACCEPTANCE_ELIGIBLE"
    return OrdersGovernedAcceptanceResult(
        status=status,
        candidate_state=candidate_state,
        blockers=tuple(dict.fromkeys(blockers)),
        lifecycle_verified=lifecycle_verified,
    )


def assess_orders_with_senior_engineering(
    *,
    generator_id: str,
    reviewer_id: str,
    verifier_id: str,
    candidate_id: str,
    artifact_sha256: str,
    frontend_operations: tuple[str, ...],
    backend_operations: tuple[str, ...],
    frontend_evidence: dict[str, str],
    backend_evidence: dict[str, str],
    promotion: GovernedCandidatePromotionService | None,
    evidence: GovernedTrustedEvidenceService | None,
    runtime_evidence_id: str | None,
    durable_evidence_id: str | None,
    lifecycle_evidence_id: str | None,
    persistence_entities: tuple[str, ...] = ("Order", "OrderLine"),
    backend_persisted_entities: tuple[str, ...] = ("Order", "OrderLine"),
    shared_auth_models: bool = True,
    external_coherence_findings: tuple[str, ...] = (),
    mandatory_full_stack_blockers: tuple[str, ...] = (),
) -> tuple[OrdersGovernedAcceptanceResult, SeniorEngineeringAssessmentResult | SeniorEngineeringVerdict]:
    gov = assess_orders_governed_acceptance(
        candidate_id=candidate_id,
        promotion=promotion,
        evidence=evidence,
        runtime_evidence_id=runtime_evidence_id,
        durable_evidence_id=durable_evidence_id,
        lifecycle_evidence_id=lifecycle_evidence_id,
        mandatory_full_stack_blockers=mandatory_full_stack_blockers,
    )
    engineering = evaluate_senior_engineering_acceptance(
        generator_id=generator_id,
        reviewer_id=reviewer_id,
        verifier_id=verifier_id,
        frontend_evidence=frontend_evidence,
        backend_evidence=backend_evidence,
        frontend_operations=frontend_operations,
        backend_operations=backend_operations,
        persistence_entities=persistence_entities,
        backend_persisted_entities=backend_persisted_entities,
        shared_auth_models=shared_auth_models,
        evidence_service=evidence,
        candidate_id=candidate_id,
        artifact_sha256=artifact_sha256,
        external_coherence_findings=external_coherence_findings,
    )
    if gov.status != "ACCEPTANCE_ELIGIBLE":
        return gov, SeniorEngineeringVerdict.ACCEPTANCE_BLOCKED
    return gov, engineering
