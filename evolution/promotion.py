"""
Evolution promotion control.

This module controls the promotion lifecycle for evolved ISR candidates.

It does not deploy software. It records governed promotion intent and
rollback state.
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Literal, Optional, Protocol

import httpx
from pydantic import BaseModel, Field

from .governance_safety import (
    EvolutionEvidence,
    SafetyInterlockEngine,
    SafetyInterlockPolicy,
    SafetyInterlockReport,
)
from .models import utcnow
from .utils import deterministic_id


class PromotionError(Exception):
    """Base error for promotion control."""


class GovernanceDecision(BaseModel):
    """Decision returned by a governance authority."""

    decision: Literal[
        "ALLOW",
        "DENY",
        "REQUIRE_APPROVAL",
    ]

    reason: str = ""

    constraints: List[Dict[str, Any]] = Field(default_factory=list)
    required_approvals: List[Dict[str, Any]] = Field(default_factory=list)


class GovernancePromotionRequest(BaseModel):
    """Request sent to a governance authority."""

    promotion_request_id: str

    proposal_id: str
    candidate_id: str

    environment: str

    evidence: EvolutionEvidence
    safety_report: Optional[SafetyInterlockReport] = None


class GovernanceGateway(Protocol):
    """Abstract governance gateway."""

    def evaluate_promotion(
        self,
        request: GovernancePromotionRequest,
    ) -> GovernanceDecision:
        ...


class StaticGovernanceGateway:
    """Static governance gateway for tests and local development."""

    def __init__(
        self,
        decision: str = "ALLOW",
        reason: str = "Static governance decision.",
    ) -> None:
        self._decision = decision
        self._reason = reason

    def evaluate_promotion(
        self,
        request: GovernancePromotionRequest,
    ) -> GovernanceDecision:
        return GovernanceDecision(
            decision=self._decision,
            reason=self._reason,
        )


class HttpGovernanceGateway:
    """
    HTTP gateway for the Phase 28 Governance Kernel.

    This gateway fails closed when governance is unavailable.
    """

    def __init__(
        self,
        base_url: str,
        timeout_seconds: float = 5.0,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._timeout_seconds = timeout_seconds

    def evaluate_promotion(
        self,
        request: GovernancePromotionRequest,
    ) -> GovernanceDecision:
        url = f"{self._base_url}/v1/governance/evaluate"

        payload = {
            "subject_type": "EVOLUTION_PROMOTION",
            "subject_id": request.promotion_request_id,
            "action": "PROMOTE_EVOLVED_ISR",
            "actor": {
                "actor_type": "SERVICE",
                "actor_id": "promotion_control_engine",
                "roles": [],
                "delegated_authority": [],
            },
            "context": {
                "proposal_id": request.proposal_id,
                "candidate_id": request.candidate_id,
                "environment": request.environment,
                "safety_passed": (
                    request.safety_report.passed
                    if request.safety_report
                    else None
                ),
            },
            "evidence_refs": [
                f"promotion_request:{request.promotion_request_id}",
                f"proposal:{request.proposal_id}",
                f"candidate:{request.candidate_id}",
            ],
        }

        try:
            with httpx.Client(timeout=self._timeout_seconds) as client:
                response = client.post(url, json=payload)
                response.raise_for_status()

                return GovernanceDecision.model_validate(response.json())

        except Exception as exc:
            return GovernanceDecision(
                decision="DENY",
                reason=f"Governance Kernel unavailable or error: {exc}",
            )


class PromotionRequestStatus(str, Enum):
    """Lifecycle status for a promotion request."""

    DRAFT = "DRAFT"
    SAFETY_CHECKS_PASSED = "SAFETY_CHECKS_PASSED"
    SAFETY_FAILED = "SAFETY_FAILED"
    GOVERNANCE_PENDING = "GOVERNANCE_PENDING"
    GOVERNANCE_DENIED = "GOVERNANCE_DENIED"
    APPROVED = "APPROVED"
    PROMOTED = "PROMOTED"
    ROLLED_BACK = "ROLLED_BACK"
    REJECTED = "REJECTED"


class PromotionControlPolicy(BaseModel):
    """Policy controlling promotion behavior."""

    require_safety_checks: bool = True

    auto_submit_governance: bool = True

    governance_required_environments: List[str] = Field(
        default_factory=lambda: ["production", "staging"]
    )

    allow_auto_approval_when_governance_allow: bool = True

    fail_closed_if_governance_unavailable: bool = True


class PromotionRequest(BaseModel):
    """Promotion request aggregate."""

    id: str

    proposal_id: str
    candidate_id: str

    environment: str
    actor_id: str

    status: PromotionRequestStatus = PromotionRequestStatus.DRAFT

    evidence: Optional[EvolutionEvidence] = None
    safety_report: Optional[SafetyInterlockReport] = None
    governance_decision: Optional[GovernanceDecision] = None

    approval: Optional[Dict[str, Any]] = None

    rollback_plan: Optional[Dict[str, Any]] = None

    error: Optional[str] = None

    created_at: str
    updated_at: str

    promoted_at: Optional[str] = None
    rolled_back_at: Optional[str] = None


class PromotionPacket(BaseModel):
    """Governance-ready promotion packet."""

    request: PromotionRequest

    evidence: Optional[EvolutionEvidence] = None
    safety_report: Optional[SafetyInterlockReport] = None
    governance_decision: Optional[GovernanceDecision] = None

    created_at: str


class PromotionControlEngine:
    """Controls promotion requests for evolved ISR candidates."""

    def __init__(
        self,
        safety_engine: Optional[SafetyInterlockEngine] = None,
        governance_gateway: Optional[GovernanceGateway] = None,
        policy: Optional[PromotionControlPolicy] = None,
        safety_policy: Optional[SafetyInterlockPolicy] = None,
        base_engine=None,
        evidence_collector=None,
    ) -> None:
        self.safety_engine = safety_engine or SafetyInterlockEngine()
        self.governance_gateway = governance_gateway
        self.policy = policy or PromotionControlPolicy()
        self.safety_policy = safety_policy or SafetyInterlockPolicy()
        self.base_engine = base_engine
        self.evidence_collector = evidence_collector

        self.requests: Dict[str, PromotionRequest] = {}

    # ------------------------------------------------------------------
    # Promotion lifecycle
    # ------------------------------------------------------------------

    def create_promotion_request(
        self,
        proposal_id: str,
        candidate_id: str,
        environment: str,
        actor_id: str,
        evidence: Optional[EvolutionEvidence] = None,
    ) -> PromotionRequest:
        if evidence is None and self.evidence_collector:
            evidence = self.evidence_collector.collect(
                proposal_id,
                candidate_id,
            )

        if evidence is None:
            raise PromotionError(
                "Evolution evidence is required for promotion."
            )

        created_at = utcnow().isoformat()

        request_id = deterministic_id(
            "promotion_request",
            {
                "proposal_id": proposal_id,
                "candidate_id": candidate_id,
                "environment": environment,
                "created_at": created_at,
            },
        )

        request = PromotionRequest(
            id=request_id,
            proposal_id=proposal_id,
            candidate_id=candidate_id,
            environment=environment,
            actor_id=actor_id,
            status=PromotionRequestStatus.DRAFT,
            evidence=evidence,
            rollback_plan=evidence.rollback_plan,
            created_at=created_at,
            updated_at=created_at,
        )

        self.requests[request_id] = request

        if self.policy.require_safety_checks:
            safety_report = self.safety_engine.evaluate(
                evidence=evidence,
                policy=self.safety_policy,
            )

            request.safety_report = safety_report

            if not safety_report.passed:
                request.status = PromotionRequestStatus.SAFETY_FAILED
                request.error = "Safety interlocks failed."
                self._touch(request)
                self._record_history(
                    request,
                    "promotion_safety_failed",
                    actor_id,
                )
                return request

        request.status = PromotionRequestStatus.SAFETY_CHECKS_PASSED
        self._touch(request)

        if self._governance_required(environment):
            if self.policy.auto_submit_governance:
                return self.submit_governance(request_id, actor_id)

            request.status = PromotionRequestStatus.GOVERNANCE_PENDING
            self._touch(request)
            self._record_history(
                request,
                "promotion_governance_pending",
                actor_id,
            )
            return request

        request.status = PromotionRequestStatus.APPROVED
        self._touch(request)
        self._record_history(
            request,
            "promotion_approved_without_governance_requirement",
            actor_id,
        )

        return request

    def submit_governance(
        self,
        request_id: str,
        actor_id: str,
    ) -> PromotionRequest:
        request = self._get_request(request_id)

        if request.status != PromotionRequestStatus.SAFETY_CHECKS_PASSED:
            raise PromotionError(
                "Governance submission is only allowed after safety checks pass."
            )

        if not self.governance_gateway:
            if (
                self.policy.fail_closed_if_governance_unavailable
                and self._governance_required(request.environment)
            ):
                decision = GovernanceDecision(
                    decision="DENY",
                    reason="Governance gateway is unavailable.",
                )
            else:
                decision = GovernanceDecision(
                    decision="ALLOW",
                    reason="Governance is not required.",
                )
        else:
            governance_request = GovernancePromotionRequest(
                promotion_request_id=request.id,
                proposal_id=request.proposal_id,
                candidate_id=request.candidate_id,
                environment=request.environment,
                evidence=request.evidence,
                safety_report=request.safety_report,
            )

            decision = self.governance_gateway.evaluate_promotion(
                governance_request
            )

        request.governance_decision = decision

        if decision.decision == "ALLOW":
            if self.policy.allow_auto_approval_when_governance_allow:
                request.status = PromotionRequestStatus.APPROVED
            else:
                request.status = PromotionRequestStatus.GOVERNANCE_PENDING

        elif decision.decision == "REQUIRE_APPROVAL":
            request.status = PromotionRequestStatus.GOVERNANCE_PENDING

        else:
            request.status = PromotionRequestStatus.GOVERNANCE_DENIED
            request.error = decision.reason

        self._touch(request)
        self._record_history(
            request,
            "promotion_governance_evaluated",
            actor_id,
        )

        return request

    def approve(
        self,
        request_id: str,
        approver_id: str,
        comments: str = "",
    ) -> PromotionRequest:
        request = self._get_request(request_id)

        if request.status != PromotionRequestStatus.GOVERNANCE_PENDING:
            raise PromotionError(
                "Approval is only allowed for GOVERNANCE_PENDING requests."
            )

        request.approval = {
            "approver_id": approver_id,
            "comments": comments,
            "approved_at": utcnow().isoformat(),
        }

        request.status = PromotionRequestStatus.APPROVED

        self._touch(request)
        self._record_history(
            request,
            "promotion_approved",
            approver_id,
        )

        return request

    def promote(
        self,
        request_id: str,
        actor_id: str,
    ) -> PromotionRequest:
        request = self._get_request(request_id)

        if request.status != PromotionRequestStatus.APPROVED:
            raise PromotionError(
                "Promotion is only allowed for APPROVED requests."
            )

        request.status = PromotionRequestStatus.PROMOTED
        request.promoted_at = utcnow().isoformat()

        self._touch(request)
        self._record_history(
            request,
            "promotion_completed",
            actor_id,
        )

        return request

    def rollback(
        self,
        request_id: str,
        actor_id: str,
        reason: str = "",
    ) -> PromotionRequest:
        request = self._get_request(request_id)

        if request.status != PromotionRequestStatus.PROMOTED:
            raise PromotionError(
                "Rollback is only allowed for PROMOTED requests."
            )

        request.status = PromotionRequestStatus.ROLLED_BACK
        request.rolled_back_at = utcnow().isoformat()

        if request.rollback_plan is None:
            request.rollback_plan = {}

        request.rollback_plan["rollback_reason"] = reason

        self._touch(request)
        self._record_history(
            request,
            "promotion_rolled_back",
            actor_id,
        )

        return request

    def get_request(self, request_id: str) -> PromotionRequest:
        return self._get_request(request_id)

    def get_packet(self, request_id: str) -> PromotionPacket:
        request = self._get_request(request_id)

        return PromotionPacket(
            request=request,
            evidence=request.evidence,
            safety_report=request.safety_report,
            governance_decision=request.governance_decision,
            created_at=utcnow().isoformat(),
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _get_request(self, request_id: str) -> PromotionRequest:
        request = self.requests.get(request_id)

        if not request:
            raise PromotionError(
                f"Promotion request not found: {request_id}"
            )

        return request

    def _touch(self, request: PromotionRequest) -> None:
        request.updated_at = utcnow().isoformat()

    def _governance_required(self, environment: str) -> bool:
        required_environments = {
            item.lower()
            for item in self.policy.governance_required_environments
        }

        return environment.lower() in required_environments

    def _record_history(
        self,
        request: PromotionRequest,
        event_type: str,
        actor_id: str,
    ) -> None:
        if not self.base_engine:
            return

        history = getattr(self.base_engine, "history", None)

        if not history:
            return

        history.record(
            proposal_id=request.proposal_id,
            event_type=event_type,
            actor_id=actor_id,
            details={
                "promotion_request_id": request.id,
                "candidate_id": request.candidate_id,
                "environment": request.environment,
                "status": request.status.value,
            },
        )


class SimpleEvolutionEvidenceCollector:
    """
    Collects evidence from the Phase 21 engine stack.

    This collector is intentionally conservative. Production deployments may
    replace it with a richer collector that includes compiler reports,
    feedback reports, knowledge graph evidence, and campaign memory.
    """

    def __init__(
        self,
        base_engine,
        candidate_engine=None,
    ) -> None:
        self.base_engine = base_engine
        self.candidate_engine = candidate_engine

    def collect(
        self,
        proposal_id: str,
        candidate_id: str,
    ) -> EvolutionEvidence:
        proposal = self.base_engine._get_proposal(proposal_id)

        candidate = self.base_engine.candidates.get(candidate_id)

        if not candidate:
            raise PromotionError(
                f"Candidate not found: {candidate_id}"
            )

        candidate_engine = self.candidate_engine or getattr(
            self.base_engine,
            "candidate_engine",
            None,
        )

        evaluation = None

        if candidate_engine:
            if hasattr(candidate_engine, "get_evaluations"):
                evaluations = candidate_engine.get_evaluations(proposal_id)
            else:
                evaluations = list(
                    getattr(candidate_engine, "evaluations", {})
                    .get(proposal_id, {})
                    .values()
                )

            for item in evaluations:
                if item.candidate_id == candidate_id:
                    evaluation = item
                    break

        simulation_status = None
        complexity = None

        if evaluation and getattr(evaluation, "simulation_id", None):
            simulation = self.base_engine.simulations.get(
                evaluation.simulation_id
            )

            if simulation:
                simulation_status = simulation.status
                complexity = simulation.metrics.get("complexity")

        verification_valid = None

        if evaluation and evaluation.verification:
            verification_valid = evaluation.verification.valid

        fitness_passed = None
        objectives = {}
        constraints = {}

        if evaluation and evaluation.fitness:
            fitness_passed = evaluation.fitness.passed
            objectives = dict(evaluation.fitness.objectives)
            constraints = dict(evaluation.fitness.constraints)

        compiler_passed = constraints.get(
            "compiler_all_required_backends_succeeded"
        )

        if compiler_passed is None:
            compiler_passed = constraints.get(
                "compiler_compiler_configuration_valid"
            )

        feedback_passed = constraints.get(
            "feedback_sufficient_feedback_evidence"
        )

        critical_incident = (
            constraints.get("feedback_no_critical_incidents") is False
        )

        critical_security_finding = (
            constraints.get("feedback_no_critical_security_findings") is False
        )

        pareto_selected = (
            getattr(proposal, "selected_candidate_id", None)
            == candidate_id
        )

        public_api_removed = False

        if evaluation and evaluation.verification:
            for issue in evaluation.verification.issues:
                if getattr(issue, "code", "") == "PUBLIC_API_REMOVED":
                    public_api_removed = True
                    break

        rollback_plan = {
            "parent_isr_hash": candidate.base_isr_hash,
            "steps": [
                "Restore parent ISR as authoritative ISR.",
                "Mark promoted candidate as rolled back.",
                "Emit rollback audit event.",
                "Notify governed systems.",
            ],
            "automated": False,
        }

        return EvolutionEvidence(
            proposal_id=proposal_id,
            candidate_id=candidate_id,
            isr_content_hash=candidate.content_hash,
            simulation_status=simulation_status,
            verification_valid=verification_valid,
            fitness_passed=fitness_passed,
            objectives=objectives,
            constraints=constraints,
            compiler_passed=compiler_passed,
            feedback_passed=feedback_passed,
            critical_incident=critical_incident,
            critical_security_finding=critical_security_finding,
            pareto_selected=pareto_selected,
            complexity=complexity,
            public_api_removed=public_api_removed,
            breaking_changes_allowed=getattr(
                proposal.request,
                "allow_breaking_changes",
                False,
            ),
            rollback_plan=rollback_plan,
        )
