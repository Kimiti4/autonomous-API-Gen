"""
Phase 28 — Approval Workflow Engine.

Routes actions through required approvals (Milestone 3). Supports human,
organizational, and bounded autonomous approval; enforces timeouts and
expiration. By default, a missing approval blocks execution
(timeout_policy DENY_ON_TIMEOUT).
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional

from constitutional_architecture.governance.schemas import (
    ApprovalDecision,
    ApprovalRecord,
    ApprovalRequirement,
    ApprovalStatus,
    Constraint,
    Decision,
    TimeoutPolicy,
)

_DEFAULT_TIMEOUT = 48 * 3600  # seconds


class ApprovalWorkflowEngine:
    def __init__(self) -> None:
        self._approvals: Dict[str, ApprovalRecord] = {}
        self._evaluation_approvals: Dict[str, List[str]] = {}
        self._now: Optional[datetime] = None

    def set_clock(self, now: datetime) -> None:
        self._now = now

    def _utcnow(self) -> datetime:
        return self._now or datetime.now(timezone.utc)

    def create_approval_request(
        self,
        evaluation_id: str,
        requirements: List[ApprovalRequirement],
    ) -> List[ApprovalRecord]:
        records: List[ApprovalRecord] = []
        for requirement in requirements:
            record = ApprovalRecord(
                id=f"approval_{uuid.uuid4().hex[:10]}",
                evaluation_id=evaluation_id,
                requirement=requirement,
                approver_type=requirement.approver_type.value,
                approver_id=requirement.approver_id or "",
                status=ApprovalStatus.PENDING,
            )
            self._approvals[record.id] = record
            records.append(record)
        self._evaluation_approvals[evaluation_id] = [
            r.id for r in records
        ]
        return records

    def submit_decision(
        self,
        approval_id: str,
        decision: ApprovalDecision,
        *,
        comments: Optional[str] = None,
        approved_constraints: Optional[List[Constraint]] = None,
    ) -> ApprovalRecord:
        record = self._approvals[approval_id]
        if record.status is not ApprovalStatus.PENDING:
            raise ValueError(
                f"Approval {approval_id} is already {record.status.value}."
            )
        record.decision = decision
        record.status = (
            ApprovalStatus.APPROVED
            if decision is ApprovalDecision.APPROVED
            else ApprovalStatus.REJECTED
            if decision is ApprovalDecision.REJECTED
            else ApprovalStatus.ABSTAINED
        )
        record.comments = comments
        record.approved_constraints = approved_constraints or []
        record.decided_at = self._utcnow()
        return record

    def refresh_timeouts(self) -> None:
        """Expires PENDING approvals whose timeout has elapsed."""
        now = self._utcnow()
        for record in self._approvals.values():
            if record.status is not ApprovalStatus.PENDING:
                continue
            if self._is_expired(record, now):
                record.status = ApprovalStatus.EXPIRED
                record.decision = ApprovalDecision.EXPIRED

    def _is_expired(self, record: ApprovalRecord, now: datetime) -> bool:
        duration = record.requirement.timeout_duration
        timeout = self._parse_duration(duration) if duration else _DEFAULT_TIMEOUT
        expiry = record.created_at.timestamp() + timeout
        return now.timestamp() > expiry

    def approve(
        self,
        evaluation_id: str,
        required: List[ApprovalRequirement],
    ) -> Decision:
        """Finalize an action after approvals: rejected or denied-on-timeout
        blocks execution; all required approvals approved allows it."""
        self.refresh_timeouts()
        records = [
            self._approvals[a]
            for a in self._evaluation_approvals.get(evaluation_id, [])
        ]
        for requirement in required:
            matching = [
                r
                for r in records
                if r.requirement.approver_type == requirement.approver_type
                and (r.requirement.approver_id or "")
                == (requirement.approver_id or "")
            ]
            if not matching:
                return Decision.REQUIRE_APPROVAL
            for record in matching:
                if record.status is ApprovalStatus.REJECTED:
                    return Decision.DENY
            if any(
                r.status is ApprovalStatus.EXPIRED
                and r.requirement.timeout_policy is TimeoutPolicy.DENY_ON_TIMEOUT
                for r in matching
            ):
                return Decision.DENY
            if requirement.required and not any(
                r.status is ApprovalStatus.APPROVED for r in matching
            ):
                return Decision.REQUIRE_APPROVAL
        return Decision.ALLOW

    @staticmethod
    def _parse_duration(duration: str) -> float:
        """Minimal ISO-8601 duration parser: PT{n}H / PT{n}M / P{n}D."""
        text = duration.strip().upper()
        total = 0.0
        number = ""
        for char in text:
            if char.isdigit() or char == ".":
                number += char
            elif char in "HMSD":
                if not number:
                    raise ValueError(f"Invalid duration: {duration}")
                value = float(number)
                if char == "D":
                    total += value * 86400
                elif char == "H":
                    total += value * 3600
                elif char == "M":
                    total += value * 60
                else:
                    total += value
                number = ""
        if not number and total == 0:
            raise ValueError(f"Invalid duration: {duration}")
        return total

    def approvals_for(self, evaluation_id: str) -> List[ApprovalRecord]:
        return [
            self._approvals[a]
            for a in self._evaluation_approvals.get(evaluation_id, [])
        ]

    def all_approvals(
        self, status: Optional[ApprovalStatus] = None
    ) -> List[ApprovalRecord]:
        records = sorted(self._approvals.values(), key=lambda r: r.created_at)
        if status is not None:
            records = [r for r in records if r.status is status]
        return records

    def get(self, approval_id: str) -> ApprovalRecord:
        return self._approvals[approval_id]
