"""
Learning governance engine.
"""

from __future__ import annotations

from typing import Dict, List

from ..evolution_integration.engine import EvolutionFitnessIntegrationEngine
from ..models import LearningInsight
from ..utils import deterministic_id, utcnow
from .models import (
    GovernanceSyncReport,
    KillSwitchState,
    LearningApprovalRequest,
    LearningGovernancePolicy,
)
from .quality import EvidenceQualityGate
from .safety import LearningSafetyEngine


class LearningGovernanceEngine:
    """Governs learning-driven evolutionary feedback."""

    def __init__(
        self,
        integration_engine: EvolutionFitnessIntegrationEngine,
        policy: LearningGovernancePolicy | None = None,
    ) -> None:
        self.integration_engine = integration_engine
        self.policy = policy or LearningGovernancePolicy()

        self.quality_gate = EvidenceQualityGate(self.policy)
        self.safety_engine = LearningSafetyEngine(self.policy)

        self.kill_switch = KillSwitchState()

        self.approvals: Dict[str, LearningApprovalRequest] = {}

    # ------------------------------------------------------------------
    # Governed synchronization
    # ------------------------------------------------------------------

    def evaluate_sync(self, scope: str = "platform") -> GovernanceSyncReport:
        bundle = self.integration_engine.generate_feedback(scope=scope)

        if bundle.status == "NO_ACTION":
            return GovernanceSyncReport(
                bundle_id=bundle.id,
                scope=scope,
                status="NO_ACTION",
            )

        insights = self._collect_insights(bundle.source_insight_ids)

        quality = self.quality_gate.evaluate(bundle.id, insights)

        safety = self.safety_engine.evaluate(
            bundle,
            quality,
            self.kill_switch.enabled,
        )

        return GovernanceSyncReport(
            bundle_id=bundle.id,
            scope=scope,
            status="EVALUATED",
            quality=quality,
            safety=safety,
        )

    def governed_sync(
        self,
        scope: str = "platform",
        requested_by: str = "system",
        auto_submit: bool = True,
    ) -> GovernanceSyncReport:
        report = self.evaluate_sync(scope=scope)

        if report.status == "NO_ACTION":
            return report

        if not report.safety or not report.safety.allowed:
            report.status = "BLOCKED"
            return report

        if report.safety.required_human_approval:
            approval = self._get_or_create_approval(
                bundle_id=report.bundle_id,
                scope=scope,
                requested_by=requested_by,
            )

            report.approval_id = approval.id

            if approval.status == "APPROVED":
                return self._submit(
                    report=report,
                    auto_submit=auto_submit,
                )

            report.status = "PENDING_APPROVAL"

            return report

        return self._submit(
            report=report,
            auto_submit=auto_submit,
        )

    # ------------------------------------------------------------------
    # Approvals
    # ------------------------------------------------------------------

    def approve(
        self,
        approval_id: str,
        approver_id: str,
        comments: str = "",
        auto_submit: bool = True,
    ) -> GovernanceSyncReport:
        approval = self.approvals.get(approval_id)

        if not approval:
            raise KeyError(f"Approval request not found: {approval_id}")

        if approval.status != "PENDING":
            raise ValueError("Approval request is not pending.")

        approval.status = "APPROVED"
        approval.decided_by = approver_id
        approval.decided_at = utcnow().isoformat()
        approval.comments = comments

        report = GovernanceSyncReport(
            bundle_id=approval.bundle_id,
            scope=approval.scope,
            status="APPROVED",
            approval_id=approval.id,
        )

        if auto_submit and self.policy.auto_submit_after_approval:
            return self._submit(report=report, auto_submit=True)

        return report

    def reject(
        self,
        approval_id: str,
        approver_id: str,
        comments: str = "",
    ) -> GovernanceSyncReport:
        approval = self.approvals.get(approval_id)

        if not approval:
            raise KeyError(f"Approval request not found: {approval_id}")

        if approval.status != "PENDING":
            raise ValueError("Approval request is not pending.")

        approval.status = "REJECTED"
        approval.decided_by = approver_id
        approval.decided_at = utcnow().isoformat()
        approval.comments = comments

        return GovernanceSyncReport(
            bundle_id=approval.bundle_id,
            scope=approval.scope,
            status="REJECTED",
            approval_id=approval.id,
        )

    # ------------------------------------------------------------------
    # Kill switch
    # ------------------------------------------------------------------

    def activate_kill_switch(
        self,
        reason: str,
        activated_by: str,
    ) -> KillSwitchState:
        self.kill_switch.enabled = True
        self.kill_switch.reason = reason
        self.kill_switch.activated_by = activated_by
        self.kill_switch.activated_at = utcnow().isoformat()

        self.kill_switch.deactivated_by = None
        self.kill_switch.deactivated_at = None

        return self.kill_switch

    def deactivate_kill_switch(
        self,
        deactivated_by: str,
        reason: str = "",
    ) -> KillSwitchState:
        self.kill_switch.enabled = False
        self.kill_switch.deactivated_by = deactivated_by
        self.kill_switch.deactivated_at = utcnow().isoformat()

        if reason:
            self.kill_switch.reason = reason

        return self.kill_switch

    # ------------------------------------------------------------------
    # Reporting
    # ------------------------------------------------------------------

    def report(self) -> Dict:
        pending_approvals = sum(
            1
            for approval in self.approvals.values()
            if approval.status == "PENDING"
        )

        approved = sum(
            1
            for approval in self.approvals.values()
            if approval.status == "APPROVED"
        )

        rejected = sum(
            1
            for approval in self.approvals.values()
            if approval.status == "REJECTED"
        )

        return {
            "kill_switch_enabled": self.kill_switch.enabled,
            "approval_count": len(self.approvals),
            "pending_approvals": pending_approvals,
            "approved_approvals": approved,
            "rejected_approvals": rejected,
        }

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _submit(
        self,
        report: GovernanceSyncReport,
        auto_submit: bool,
    ) -> GovernanceSyncReport:
        if not auto_submit:
            report.status = "READY_TO_SUBMIT"
            return report

        submission = self.integration_engine.submit_feedback(report.bundle_id)

        self.safety_engine.record_submission(report.scope)

        report.submission_id = submission.submission_id
        report.status = submission.status

        return report

    def _get_or_create_approval(
        self,
        bundle_id: str,
        scope: str,
        requested_by: str,
    ) -> LearningApprovalRequest:
        for approval in self.approvals.values():
            if approval.bundle_id == bundle_id:
                return approval

        approval_id = deterministic_id(
            "learning_approval_request",
            {
                "bundle_id": bundle_id,
                "scope": scope,
            },
        )

        approval = LearningApprovalRequest(
            id=approval_id,
            bundle_id=bundle_id,
            scope=scope,
            status="PENDING",
            requested_by=requested_by,
        )

        self.approvals[approval_id] = approval

        return approval

    def _collect_insights(
        self,
        insight_ids: List[str],
    ) -> List[LearningInsight]:
        wanted = set(insight_ids)

        insights: Dict[str, LearningInsight] = {}

        analytics_engine = getattr(
            self.integration_engine,
            "analytics_engine",
            None,
        )

        if analytics_engine and hasattr(analytics_engine, "insights"):
            for insight in analytics_engine.insights.values():
                if insight.id in wanted:
                    insights[insight.id] = insight

        learning_engine = getattr(
            self.integration_engine,
            "learning_engine",
            None,
        )

        if learning_engine and hasattr(learning_engine, "insights"):
            for insight in learning_engine.insights.values():
                if insight.id in wanted:
                    insights[insight.id] = insight

        return list(insights.values())
