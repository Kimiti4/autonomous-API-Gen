"""
Phase 28 — Governance Dashboard kernel client.

A thin client over the Governance Kernel implementing the dashboard
contract (spec §8). v0.1 runs in-process against a kernel instance; the
interface is endpoint-shaped so a remote kernel API can be swapped in
without touching view code. All calls fail closed: kernel errors surface
as KernelUnavailableError.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import List, Optional

from constitutional_architecture.governance.dashboard import view_models as vm
from constitutional_architecture.governance.dashboard.errors import (
    DashboardError,
    KernelUnavailableError,
    NotFoundError,
    ValidationError,
)
from constitutional_architecture.governance.dashboard.service import (
    DashboardAuthorizationError,
    DashboardService,
)
from constitutional_architecture.governance.kernel import GovernanceKernel
from constitutional_architecture.governance.schemas import (
    Actor,
    ApprovalDecision,
    Decision,
)

_SENSITIVE_SUFFIXES = ("secret", "token", "password", "passwd", "credential", "api_key", "private_key")


def json_safe(value):
    """Strip pydantic datetimes/enums to plain JSON-compatible structures."""
    return json.loads(json.dumps(value, default=str))


class GovernanceDashboardClient:
    """Read + guarded-mutation client. Mutations go through the kernel's
    DashboardService, which re-checks authorization and audits."""

    def __init__(
        self,
        kernel: GovernanceKernel,
        *,
        dashboard: Optional[DashboardService] = None,
        redact_keys: tuple = _SENSITIVE_SUFFIXES,
    ) -> None:
        self.kernel = kernel
        self.dashboard = dashboard or DashboardService(kernel)
        self.redact_keys = redact_keys

    # ── helpers ──────────────────────────────────────────────────────────
    def _guard(self, fn, *args, **kwargs):
        try:
            return fn(*args, **kwargs)
        except KernelUnavailableError:
            raise
        except DashboardError:
            raise
        except DashboardAuthorizationError:
            raise
        except ValueError as exc:
            raise ValidationError(str(exc)) from exc
        except KeyError as exc:
            raise NotFoundError(str(exc)) from exc
        except Exception as exc:
            raise KernelUnavailableError(
                f"Kernel request failed: {type(exc).__name__}", cause=exc
            ) from exc

    @staticmethod
    def _iso(value) -> Optional[str]:
        return value.isoformat() if value else None

    @staticmethod
    def _enum_str(value) -> str:
        if value is None:
            return ""
        return value.value if hasattr(value, "value") else str(value)

    # ── constitutions ────────────────────────────────────────────────────
    def list_constitutions(self) -> List[vm.ConstitutionSummaryView]:
        def _run():
            return [
                vm.ConstitutionSummaryView(
                    id=c["id"],
                    name=c["name"],
                    version=c["version"],
                    status=c["status"],
                    created_at=self._iso(c.get("created_at")),
                    created_by=c.get("created_by", ""),
                    content_hash=c.get("content_hash", ""),
                )
                for c in self.dashboard.constitution_overview()["constitutions"]
            ]

        return self._guard(_run)

    def get_constitution(self, constitution_id: str) -> vm.ConstitutionDetailView:
        def _run():
            overview = self.dashboard.constitution_overview()
            for c in overview["constitutions"]:
                if c["id"] == constitution_id:
                    return vm.ConstitutionDetailView(
                        id=c["id"],
                        name=c["name"],
                        version=c["version"],
                        status=c["status"],
                        created_at=self._iso(c.get("created_at")),
                        created_by=c.get("created_by", ""),
                        content_hash=c.get("content_hash", ""),
                        policy_domains=c.get("policy_domains", []),
                        invariants=json_safe(c.get("invariants", [])),
                        approval_requirements=json_safe(
                            [
                                r.model_dump() if hasattr(r, "model_dump") else dict(r)
                                for r in c.get("approval_requirements", [])
                            ]
                        ),
                        exception_policy=json_safe(c.get("exception_policy")),
                        parent_id=c.get("parent_id"),
                        parent_version=c.get("parent_version"),
                        effective_at=self._iso(c.get("effective_at")),
                        signature=c.get("signature"),
                    )
            raise NotFoundError(f"Constitution {constitution_id} not found.")

        return self._guard(_run)

    # ── policy sets ──────────────────────────────────────────────────────
    def list_policy_sets(self) -> List[vm.PolicySetSummaryView]:
        def _run():
            return [
                vm.PolicySetSummaryView(
                    id=p["id"],
                    name=p["name"],
                    version=p["version"],
                    status=p["status"],
                    constitution_id=p.get("constitution_id", ""),
                    created_at=self._iso(p.get("created_at")),
                    content_hash=p.get("content_hash", ""),
                )
                for p in self.dashboard.constitution_overview()["policy_sets"]
            ]

        return self._guard(_run)

    def get_policy_set(self, policy_set_id: str) -> vm.PolicySetDetailView:
        def _run():
            for p in self.dashboard.constitution_overview()["policy_sets"]:
                if p["id"] == policy_set_id:
                    return vm.PolicySetDetailView(
                        id=p["id"],
                        name=p["name"],
                        version=p["version"],
                        status=p["status"],
                        constitution_id=p.get("constitution_id", ""),
                        created_at=self._iso(p.get("created_at")),
                        content_hash=p.get("content_hash", ""),
                        rules=[
                            vm.RuleView(
                                id=r["id"],
                                name=r["name"],
                                effect=r.get("effect", ""),
                                priority=r.get("priority", 100),
                                subject_types=r.get("subject_types", []),
                                actions=r.get("actions", []),
                                conditions=json_safe(r.get("conditions", [])),
                                required_evidence=r.get("required_evidence", []),
                                required_approvals=json_safe(
                                    [
                                        a.model_dump() if hasattr(a, "model_dump") else dict(a)
                                        for a in r.get("required_approvals", [])
                                    ]
                                ),
                                constraints=json_safe(r.get("constraints", [])),
                            )
                            for r in p.get("policy_rules", [])
                        ],
                    )
            raise NotFoundError(f"Policy set {policy_set_id} not found.")

        return self._guard(_run)

    # ── evaluations ──────────────────────────────────────────────────────
    def list_evaluations(self, filters: Optional[dict] = None) -> List[vm.EvaluationSummaryView]:
        filters = filters or {}

        def _run():
            items = self.dashboard.evaluations(**filters)
            return [self._evaluation_view(item) for item in items]

        return self._guard(_run)

    def _evaluation_view(self, item: dict) -> vm.EvaluationSummaryView:
        request = item.get("request", {})
        actor = request.get("actor", {})
        decision = item.get("decision", {})
        return vm.EvaluationSummaryView(
            decision_id=item["decision_id"],
            subject_type=request.get("subject_type", ""),
            subject_id=request.get("subject_id", ""),
            action=request.get("action", ""),
            actor_id=actor.get("actor_id", ""),
            decision=getattr(decision.get("decision"), "value", decision.get("decision", "")),
            reason=decision.get("reason", ""),
            environment=(request.get("context") or {}).get("environment", ""),
            created_at=self._iso(decision.get("created_at")),
        )

    def get_decision(self, decision_id: str) -> vm.DecisionDossierView:
        return self.reconstruct_decision(decision_id)

    def reconstruct_decision(self, decision_id: str) -> vm.DecisionDossierView:
        def _run():
            dossier = self.dashboard.decision_dossier(decision_id)
            decision = dossier.get("decision", {})
            request = dossier.get("request", {})
            evidence = decision.get("required_evidence", [])
            provided = request.get("evidence_refs", [])
            missing = [e for e in evidence if e not in provided]
            return vm.DecisionDossierView(
                decision_id=decision_id,
                request=vm.redact(json_safe(request), self.redact_keys),
                decision=vm.redact(json_safe(decision), self.redact_keys),
                final_decision=dossier.get("final_decision"),
                policy_evaluations=[
                    vm.PolicyEvaluationView(
                        policy_set_id=p.get("policy_set_id", ""),
                        policy_set_version=p.get("policy_set_version", ""),
                        rule_id=p.get("rule_id", ""),
                        rule_name=p.get("rule_name", ""),
                        outcome=p.get("outcome", ""),
                        explanation=p.get("explanation", ""),
                    )
                    for p in decision.get("evaluated_policies", [])
                ],
                evidence=vm.EvidenceView(
                    required=evidence,
                    provided=provided,
                    missing=missing,
                ),
                approvals=[
                    vm.ApprovalView(
                        approval_id=a.get("id", ""),
                        status=a.get("status", ""),
                        approver_id=(a.get("requirement") or {}).get("approver_id", ""),
                        required=(a.get("requirement") or {}).get("required", True),
                        decision=a.get("decision"),
                        decided_by=a.get("decided_by"),
                        decided_at=self._iso(a.get("decided_at")),
                        comments=a.get("comments"),
                    )
                    for a in dossier.get("approvals", [])
                ],
                exceptions_applied=decision.get("exceptions_applied", []),
                audit_events=[
                    vm.AuditEventView(
                        event_id=e.get("id", ""),
                        event_type=e.get("event_type", ""),
                        actor_id=(e.get("actor") or {}).get("actor_id", ""),
                        subject_type=e.get("subject_type", ""),
                        subject_id=e.get("subject_id", ""),
                        action=e.get("action", ""),
                        decision_id=e.get("decision_id"),
                        timestamp=self._iso(e.get("timestamp")),
                        event_hash=e.get("event_hash", ""),
                        previous_event_hash=e.get("previous_event_hash", ""),
                    )
                    for e in dossier.get("audit_events", [])
                ],
                lineage=[
                    self._lineage_view(link)
                    for link in dossier.get("lineage", [])
                ],
            )

        return self._guard(_run)

    # ── approvals ────────────────────────────────────────────────────────
    def list_approvals(self, filters: Optional[dict] = None) -> List[vm.ApprovalSummaryView]:
        filters = filters or {}
        status = filters.get("status")

        def _run():
            evaluations = {e["decision_id"]: e for e in self.dashboard.evaluations()}
            records = self.dashboard.approvals(status=status)
            summaries = []
            for r in records:
                evaluation = evaluations.get(r.get("evaluation_id"), {})
                request = evaluation.get("request", {})
                requirement = r.get("requirement", {})
                summaries.append(
                    vm.ApprovalSummaryView(
                        id=r["id"],
                        evaluation_id=r.get("evaluation_id", ""),
                        approver_id=requirement.get("approver_id", ""),
                        required=requirement.get("required", True),
                        status=self._enum_str(r.get("status")),
                        created_at=self._iso(r.get("created_at")),
                        expires_at=self._iso(r.get("decided_at")),
                        subject=f"{request.get('subject_type', '')} / {request.get('subject_id', '')}",
                        action=request.get("action", ""),
                    )
                )
            return summaries

        return self._guard(_run)

    def get_approval(self, approval_id: str) -> vm.ApprovalDetailView:
        def _run():
            summary = next(
                (a for a in self.list_approvals() if a.id == approval_id),
                None,
            )
            if summary is None:
                raise NotFoundError(f"Approval {approval_id} not found.")
            record = self.kernel.approvals.get(approval_id)
            decision_id = record.evaluation_id
            dossier = self.dashboard.decision_dossier(decision_id)
            return vm.ApprovalDetailView(
                id=record.id,
                evaluation_id=decision_id,
                approver_id=(record.requirement or {}).approver_id,
                required=(record.requirement or {}).required,
                status=record.status.value,
                created_at=self._iso(record.created_at),
                expires_at=None,
                subject=summary.subject,
                action=summary.action,
                decision_summary={
                    "decision": dossier.get("final_decision")
                    or getattr(dossier.get("decision", {}).get("decision"), "value", None),
                    "reason": dossier.get("decision", {}).get("reason", ""),
                },
                evidence=dossier.get("decision", {}).get("required_evidence", []),
                constraints=dossier.get("decision", {}).get("constraints", []),
                comments=record.comments,
                decided_at=self._iso(record.decided_at),
                decided_by=record.approver_id,
            )

        return self._guard(_run)

    def submit_approval_decision(
        self,
        approval_id: str,
        actor: Actor,
        decision: str,
        comments: Optional[str] = None,
    ) -> dict:
        def _run():
            if decision == "REJECTED":
                record = self.dashboard.reject(
                    approval_id, actor, comments=comments or ""
                )
            else:
                record = self.dashboard.approve(
                    approval_id, actor, comments=comments or ""
                )
            return {"id": record["id"], "status": record["status"]}

        return self._guard(_run)

    # ── exceptions ───────────────────────────────────────────────────────
    def list_exceptions(self, filters: Optional[dict] = None) -> List[vm.ExceptionSummaryView]:
        status = (filters or {}).get("status")

        def _run():
            return [
                vm.ExceptionSummaryView(
                    id=e["id"],
                    name=e["name"],
                    status=self._enum_str(e["status"]),
                    granted_by=e.get("granted_by", ""),
                    created_at=self._iso(e.get("created_at")),
                    expires_at=self._iso(e.get("expires_at")),
                    use_count=(e.get("scope") or {}).get("use_count", 0),
                    max_uses=(e.get("scope") or {}).get("max_uses"),
                )
                for e in self.dashboard.exceptions(status=status)
            ]

        return self._guard(_run)

    def get_exception(self, exception_id: str) -> vm.ExceptionDetailView:
        def _run():
            for e in self.dashboard.exceptions():
                if e["id"] == exception_id:
                    return vm.ExceptionDetailView(
                        id=e["id"],
                        name=e["name"],
                        status=self._enum_str(e["status"]),
                        granted_by=e.get("granted_by", ""),
                        created_at=self._iso(e.get("created_at")),
                        expires_at=self._iso(e.get("expires_at")),
                        use_count=(e.get("scope") or {}).get("use_count", 0),
                        max_uses=(e.get("scope") or {}).get("max_uses"),
                        justification=e.get("justification", ""),
                        scope=vm.redact(json_safe(e.get("scope", {})), self.redact_keys),
                        audit_ref=e.get("audit_ref", ""),
                    )
            raise NotFoundError(f"Exception {exception_id} not found.")

        return self._guard(_run)

    def revoke_exception(self, exception_id: str, actor: Actor) -> dict:
        def _run():
            record = self.dashboard.revoke_exception(exception_id, actor)
            return {"id": record["id"], "status": record["status"].value}

        return self._guard(_run)

    # ── audit ────────────────────────────────────────────────────────────
    def list_audit_events(self, filters: Optional[dict] = None) -> List[vm.AuditEventView]:
        filters = filters or {}

        def _run():
            return [
                vm.AuditEventView(
                    event_id=e["id"],
                    event_type=e.get("event_type", ""),
                    actor_id=(e.get("actor") or {}).get("actor_id", ""),
                    subject_type=e.get("subject_type", ""),
                    subject_id=e.get("subject_id", ""),
                    action=e.get("action", ""),
                    decision_id=e.get("decision_id"),
                    timestamp=self._iso(e.get("timestamp")),
                    event_hash=e.get("event_hash", ""),
                    previous_event_hash=e.get("previous_event_hash", ""),
                )
                for e in self.dashboard.audit_events(**filters)
            ]

        return self._guard(_run)

    def get_audit_event(self, event_id: str) -> dict:
        def _run():
            for e in self.dashboard.audit_events():
                if e["id"] == event_id:
                    return vm.redact(json_safe(e), self.redact_keys)
            raise NotFoundError(f"Audit event {event_id} not found.")

        return self._guard(_run)

    def verify_audit_chain(self) -> vm.AuditIntegrityView:
        def _run():
            result = self.dashboard.verify_chain()
            events = self.dashboard.audit_events()
            return vm.AuditIntegrityView(
                status=result["status"],
                verified_events=len(events),
                first_invalid_event=json_safe(result.get("first_broken_event")),
                latest_event_hash=events[-1]["event_hash"] if events else None,
                last_verified_at=datetime.now(timezone.utc).isoformat(),
            )

        return self._guard(_run)

    # ── lineage ──────────────────────────────────────────────────────────
    def get_lineage_backward(self, artifact_id: str) -> vm.LineageTraceView:
        return self._lineage_trace(artifact_id, "backward")

    def get_lineage_forward(self, artifact_id: str) -> vm.LineageTraceView:
        return self._lineage_trace(artifact_id, "forward")

    def _lineage_trace(self, artifact_id: str, direction: str) -> vm.LineageTraceView:
        def _run():
            trace = self.dashboard.lineage_trace("ISR_REVISION", artifact_id)
            selected = trace[direction]
            return vm.LineageTraceView(
                artifact_type="ISR_REVISION",
                artifact_id=artifact_id,
                backward=selected if direction == "backward" else trace["backward"],
                forward=selected if direction == "forward" else trace["forward"],
                ancestors=[self._lineage_view(l) for l in trace["ancestors"]],
            )

        return self._guard(_run)

    def list_lineage(self) -> List[vm.LineageLinkView]:
        def _run():
            links = [
                l.model_dump() if hasattr(l, "model_dump") else dict(l)
                for l in self.kernel.lineage.all()
            ]
            return [self._lineage_view(l) for l in links]

        return self._guard(_run)

    def _lineage_view(self, link: dict) -> vm.LineageLinkView:
        return vm.LineageLinkView(
            id=link.get("id", ""),
            parent_type=link.get("parent_artifact_type", ""),
            parent_id=link.get("parent_artifact_id", ""),
            child_type=link.get("child_artifact_type", ""),
            child_id=link.get("child_artifact_id", ""),
            change_type=link.get("change_type", ""),
            decision_ref=link.get("decision_ref"),
            approval_refs=link.get("approval_refs", []),
            rollback_plan_ref=link.get("rollback_plan_ref"),
        )

    # ── health ───────────────────────────────────────────────────────────
    def governance_health(self) -> vm.HealthSummaryView:
        def _run():
            health = self.dashboard.health()
            overview = self.dashboard.constitution_overview()
            evaluations = self.dashboard.evaluations()
            recent = evaluations[-8:]
            recent_denials = sum(
                1
                for e in evaluations
                if (e.get("final_decision") or e["decision"].get("decision"))
                == getattr(Decision.DENY, "value", "DENY")
            )
            return vm.HealthSummaryView(
                active_constitution=overview["active_constitutions"][0]
                if overview["active_constitutions"]
                else None,
                active_policy_sets=[
                    p for p in overview["policy_sets"] if p.get("status") == "ACTIVE"
                ],
                recent_evaluations=[self._evaluation_view(e) for e in recent],
                recent_denials=recent_denials,
                pending_approvals=health["pending_approvals"],
                active_exceptions=health["active_exceptions"],
                expiring_exceptions=health["expiring_exceptions_24h"],
                audit_chain_status=health["audit_chain"]["status"],
                audit_chain_events=health["audit_chain"].get("events", 0),
                policy_error_count=sum(
                    1
                    for e in evaluations
                    if (e.get("decision") or {}).get("decision") == getattr(Decision.DENY, "value", "DENY")
                ),
            )

        return self._guard(_run)
