"""
Phase 28 — Governance Dashboard service (Milestone 5A).

A read-mostly governance visibility and reconstruction layer. Answers:
    1. What is governed?       — constitution / policy overview
    2. What was decided?       — evaluation explorer + health summary
    3. Why was it decided?     — decision reconstruction dossier
    4. Who approved it?        — approval queue + dossier approvals
    5. How can it be traced?   — audit explorer, chain verification, lineage

Architectural constraints (per dashboard doctrine):
  - read-only queries over kernel state; the kernel is the only backend
  - mutations (approve/reject/revoke) route through kernel APIs and are
    audited — the dashboard never writes state itself
  - dashboard actions are authorization-checked (least privilege)
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional

from constitutional_architecture.governance.kernel import GovernanceKernel
from constitutional_architecture.governance.schemas import (
    Actor,
    ApprovalDecision,
    ApprovalStatus,
    Decision,
    ExceptionStatus,
)


class DashboardAuthorizationError(PermissionError):
    pass


class DashboardService:
    """Operational console over the Governance Kernel."""

    VIEWER_ROLES = (
        "platform_operator",
        "auditor",
        "architecture_reviewer",
        "security_reviewer",
        "evolution_supervisor",
    )

    def __init__(
        self,
        kernel: GovernanceKernel,
        viewer_roles: Optional[List[str]] = None,
    ) -> None:
        self.kernel = kernel
        self.viewer_roles = list(viewer_roles or self.VIEWER_ROLES)

    # ── authorization ───────────────────────────────────────────────────
    def _authorize(self, actor: Actor) -> None:
        if not (set(actor.roles) & set(self.viewer_roles)):
            raise DashboardAuthorizationError(
                f"Actor {actor.actor_id} lacks a dashboard role "
                f"(requires one of {', '.join(self.viewer_roles)})."
            )

    # ── view 1: constitution & policy overview ──────────────────────────
    def constitution_overview(self) -> dict:
        return {
            "constitutions": [
                c.model_dump() for c in self.kernel.constitutions.list()
            ],
            "active_constitutions": [
                c.model_dump() for c in self.kernel.constitutions.active()
            ],
            "policy_sets": self.kernel.policy_sets.export_policy_sets(),
        }

    # ── view 2: evaluation explorer ─────────────────────────────────────
    def evaluations(self, **filters) -> List[dict]:
        return self.kernel.evaluations(**filters)

    # ── view 3: decision reconstruction dossier ─────────────────────────
    def decision_dossier(self, decision_id: str) -> dict:
        dossier = self.kernel.reconstruct(decision_id)
        dossier["audit_events"] = [
            e.model_dump()
            for e in self.kernel.audit_events(decision_id=decision_id)
        ]
        dossier["lineage"] = [
            link.model_dump()
            for link in self.kernel.lineage.by_decision(decision_id)
        ]
        request = dossier.get("request", {})
        dossier["constitution_version"] = self._constitution_context()
        dossier["rollback_plan_ref"] = self._rollback_refs(request)
        return dossier

    def _constitution_context(self) -> List[dict]:
        active = self.kernel.constitutions.active()
        if not active:
            return []
        return [
            {
                "constitution_id": c.id,
                "version": c.version,
                "status": c.status.value,
                "effective_at": c.effective_at,
            }
            for c in active
        ]

    @staticmethod
    def _rollback_refs(request: dict) -> Optional[str]:
        context = request.get("context", {}) or {}
        return context.get("rollback_plan_ref") or context.get("has_rollback_plan")

    # ── view 4: approval queue ──────────────────────────────────────────
    def approvals(
        self, status: Optional[str] = None
    ) -> List[dict]:
        status_enum = ApprovalStatus(status) if status else None
        return [
            a.model_dump()
            for a in self.kernel.approvals.all_approvals(status_enum)
        ]

    def approve(
        self, approval_id: str, actor: Actor, comments: str = ""
    ) -> dict:
        self._authorize(actor)
        record = self.kernel.submit_approval(
            approval_id, ApprovalDecision.APPROVED, comments=comments, actor=actor
        )
        return record.model_dump()

    def reject(
        self, approval_id: str, actor: Actor, comments: str = ""
    ) -> dict:
        self._authorize(actor)
        record = self.kernel.submit_approval(
            approval_id, ApprovalDecision.REJECTED, comments=comments, actor=actor
        )
        return record.model_dump()

    # ── view 5: exception registry ──────────────────────────────────────
    def exceptions(
        self, status: Optional[str] = None
    ) -> List[dict]:
        exceptions = self.kernel.exceptions.all()
        if status is not None:
            exceptions = [
                e for e in exceptions
                if e.status.value == status
            ]
        return [e.model_dump() for e in exceptions]

    def revoke_exception(
        self, exception_id: str, actor: Actor, justification: str = ""
    ) -> dict:
        self._authorize(actor)
        exception = self.kernel.revoke_exception(exception_id, actor=actor)
        if justification:
            self.kernel.audit.record(
                event_type="EXCEPTION_REVOKE_AUDITED",
                actor=actor,
                subject_type="GOVERNANCE_EXCEPTION",
                subject_id=exception_id,
                action="REVOKE_EXCEPTION",
                context={"justification": justification},
            )
        return exception.model_dump()

    # ── view 6: audit log explorer ──────────────────────────────────────
    def audit_events(self, **filters) -> List[dict]:
        return [e.model_dump() for e in self.kernel.audit_events(**filters)]

    def verify_chain(self) -> dict:
        """AC-2: reports VALID or the first broken event."""
        valid, first_broken = self.kernel.audit_chain_detail()
        if valid:
            return {"status": "VALID", "events": len(self.kernel.audit_events())}
        events = self.kernel.audit_events()
        return {
            "status": "BROKEN",
            "first_broken_index": first_broken,
            "first_broken_event": events[first_broken].model_dump()
            if first_broken is not None and first_broken < len(events)
            else None,
        }

    # ── view 7: lineage explorer ────────────────────────────────────────
    def lineage_trace(
        self, artifact_type: str, artifact_id: str
    ) -> dict:
        return {
            "artifact": {"type": artifact_type, "id": artifact_id},
            "backward": [
                link.model_dump()
                for link in self.kernel.lineage.trace_backward(
                    artifact_type, artifact_id
                )
            ],
            "forward": [
                link.model_dump()
                for link in self.kernel.lineage.trace_forward(
                    artifact_type, artifact_id
                )
            ],
            "ancestors": [
                link.model_dump()
                for link in self.kernel.lineage.ancestors(
                    artifact_type, artifact_id
                )
            ],
        }

    # ── view 8: governance health summary ───────────────────────────────
    def health(self) -> dict:
        evaluations = self.kernel.evaluations()
        counts: Dict[str, int] = {}
        for item in evaluations:
            decision = item.get("final_decision") or item["decision"].get("decision")
            decision = getattr(decision, "value", decision)
            counts[decision] = counts.get(decision, 0) + 1
        approvals = self.kernel.approvals.all_approvals()
        now = datetime.now(timezone.utc)
        exceptions = self.kernel.exceptions.all()
        expiring = [
            e for e in exceptions
            if e.status is ExceptionStatus.ACTIVE
            and e.expires_at <= now + timedelta(days=1)
        ]
        return {
            "total_evaluations": len(evaluations),
            "by_decision": counts,
            "pending_approvals": sum(
                1 for a in approvals if a.status is ApprovalStatus.PENDING
            ),
            "expired_approvals": sum(
                1 for a in approvals if a.status is ApprovalStatus.EXPIRED
            ),
            "active_exceptions": sum(
                1 for e in exceptions if e.status is ExceptionStatus.ACTIVE
            ),
            "expiring_exceptions_24h": len(expiring),
            "audit_chain": self.verify_chain(),
        }
