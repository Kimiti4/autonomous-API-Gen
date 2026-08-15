"""
Promotion auditing.

This module provides a tamper-evident audit trail for promotion requests.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from .utils import canonical_json, deterministic_id, sha256_hex


class PromotionAuditEvent(BaseModel):
    """Audit event for a promotion request."""

    id: str

    promotion_request_id: str

    event_type: str

    actor_id: str

    details: Dict[str, Any] = Field(default_factory=dict)

    timestamp: str

    previous_event_hash: str
    event_hash: str


class PromotionAuditVerificationReport(BaseModel):
    """Report describing promotion audit integrity."""

    promotion_request_id: str

    valid: bool

    event_count: int = 0

    first_invalid_event_id: Optional[str] = None


class PromotionAuditTrail:
    """Append-only, hash-chained promotion audit trail."""

    def __init__(self) -> None:
        self.events_by_request: Dict[str, List[PromotionAuditEvent]] = {}
        self.last_hash_by_request: Dict[str, str] = {}

    def record(
        self,
        promotion_request_id: str,
        event_type: str,
        actor_id: str,
        details: Optional[Dict[str, Any]] = None,
    ) -> PromotionAuditEvent:
        events = self.events_by_request.setdefault(promotion_request_id, [])

        previous_hash = self.last_hash_by_request.get(
            promotion_request_id,
            "genesis",
        )

        from .models import utcnow

        timestamp = utcnow().isoformat()

        event_id = deterministic_id(
            "promotion_audit_event",
            {
                "promotion_request_id": promotion_request_id,
                "event_type": event_type,
                "timestamp": timestamp,
                "previous_event_hash": previous_hash,
            },
        )

        event_hash = sha256_hex(
            canonical_json(
                {
                    "event_id": event_id,
                    "promotion_request_id": promotion_request_id,
                    "event_type": event_type,
                    "actor_id": actor_id,
                    "details": details or {},
                    "timestamp": timestamp,
                    "previous_event_hash": previous_hash,
                }
            )
        )

        event = PromotionAuditEvent(
            id=event_id,
            promotion_request_id=promotion_request_id,
            event_type=event_type,
            actor_id=actor_id,
            details=details or {},
            timestamp=timestamp,
            previous_event_hash=previous_hash,
            event_hash=event_hash,
        )

        events.append(event)

        self.last_hash_by_request[promotion_request_id] = event_hash

        return event

    def list_events(self, promotion_request_id: str) -> List[PromotionAuditEvent]:
        return list(self.events_by_request.get(promotion_request_id, []))

    def verify(self, promotion_request_id: str) -> PromotionAuditVerificationReport:
        events = self.events_by_request.get(promotion_request_id, [])

        previous_hash = "genesis"

        from .models import utcnow

        for event in events:
            if event.previous_event_hash != previous_hash:
                return PromotionAuditVerificationReport(
                    promotion_request_id=promotion_request_id,
                    valid=False,
                    event_count=len(events),
                    first_invalid_event_id=event.id,
                )

            expected_hash = sha256_hex(
                canonical_json(
                    {
                        "event_id": event.id,
                        "promotion_request_id": event.promotion_request_id,
                        "event_type": event.event_type,
                        "actor_id": event.actor_id,
                        "details": event.details,
                        "timestamp": event.timestamp,
                        "previous_event_hash": event.previous_event_hash,
                    }
                )
            )

            if event.event_hash != expected_hash:
                return PromotionAuditVerificationReport(
                    promotion_request_id=promotion_request_id,
                    valid=False,
                    event_count=len(events),
                    first_invalid_event_id=event.id,
                )

            previous_hash = event.event_hash

        return PromotionAuditVerificationReport(
            promotion_request_id=promotion_request_id,
            valid=True,
            event_count=len(events),
        )

    def reconstruct(self, promotion_request_id: str) -> List[PromotionAuditEvent]:
        return self.list_events(promotion_request_id)


class AuditedPromotionEngine:
    """Wraps a promotion engine with audit recording."""

    def __init__(self, inner, audit_trail: PromotionAuditTrail) -> None:
        self.inner = inner
        self.audit_trail = audit_trail

    def create_promotion_request(
        self,
        proposal_id: str,
        candidate_id: str,
        environment: str,
        actor_id: str,
        evidence=None,
    ):
        try:
            request = self.inner.create_promotion_request(
                proposal_id=proposal_id,
                candidate_id=candidate_id,
                environment=environment,
                actor_id=actor_id,
                evidence=evidence,
            )
        except Exception as exc:
            self.audit_trail.record(
                promotion_request_id="unknown",
                event_type="PROMOTION_OPERATION_FAILED",
                actor_id=actor_id,
                details={
                    "operation": "create_promotion_request",
                    "proposal_id": proposal_id,
                    "candidate_id": candidate_id,
                    "error": str(exc),
                },
            )

            raise

        self._record_request_state(request, actor_id)

        return request

    def submit_governance(self, request_id: str, actor_id: str):
        return self._audited_operation(
            request_id=request_id,
            actor_id=actor_id,
            operation_name="submit_governance",
            operation=lambda: self.inner.submit_governance(request_id, actor_id),
        )

    def approve(self, request_id: str, approver_id: str, comments: str = ""):
        return self._audited_operation(
            request_id=request_id,
            actor_id=approver_id,
            operation_name="approve",
            operation=lambda: self.inner.approve(
                request_id,
                approver_id,
                comments,
            ),
        )

    def promote(self, request_id: str, actor_id: str):
        return self._audited_operation(
            request_id=request_id,
            actor_id=actor_id,
            operation_name="promote",
            operation=lambda: self.inner.promote(request_id, actor_id),
        )

    def rollback(self, request_id: str, actor_id: str, reason: str = ""):
        return self._audited_operation(
            request_id=request_id,
            actor_id=actor_id,
            operation_name="rollback",
            operation=lambda: self.inner.rollback(
                request_id,
                actor_id,
                reason,
            ),
        )

    def get_request(self, request_id: str):
        return self.inner.get_request(request_id)

    def get_packet(self, request_id: str):
        return self.inner.get_packet(request_id)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _audited_operation(
        self,
        request_id: str,
        actor_id: str,
        operation_name: str,
        operation,
    ):
        try:
            request = operation()
        except Exception as exc:
            self.audit_trail.record(
                promotion_request_id=request_id,
                event_type="PROMOTION_OPERATION_FAILED",
                actor_id=actor_id,
                details={
                    "operation": operation_name,
                    "error": str(exc),
                },
            )

            raise

        self._record_request_state(request, actor_id)

        return request

    def _record_request_state(self, request, actor_id: str) -> None:
        status = str(request.status.value)

        event_type = f"PROMOTION_{status}"

        details = {
            "proposal_id": request.proposal_id,
            "candidate_id": request.candidate_id,
            "environment": request.environment,
            "status": status,
        }

        if request.governance_decision:
            details["governance_decision"] = (
                request.governance_decision.decision
            )

        if request.safety_report:
            details["safety_passed"] = request.safety_report.passed

        self.audit_trail.record(
            promotion_request_id=request.id,
            event_type=event_type,
            actor_id=actor_id,
            details=details,
        )
