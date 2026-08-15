"""
Phase 28 — Governance Exception Manager.

Handles temporary, bounded policy exceptions (Milestone 5). Exceptions are
never permanent by default: they carry a scope, a justification, an
approver, an expiration, constraints, and a revocation path. Expired or
revoked exceptions apply to nothing.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional

from constitutional_architecture.governance.schemas import (
    ExceptionScope,
    ExceptionStatus,
    GovernanceEvaluationRequest,
    GovernanceException,
)


class GovernanceExceptionManager:
    def __init__(self, require_justification: bool = True) -> None:
        self._exceptions: Dict[str, GovernanceException] = {}
        self._require_justification = require_justification

    def create(
        self,
        name: str,
        justification: str,
        *,
        scope: Optional[ExceptionScope] = None,
        granted_by: str = "governance_kernel",
        expires_at: Optional[datetime] = None,
        max_uses: Optional[int] = None,
        environment: Optional[str] = None,
    ) -> GovernanceException:
        if self._require_justification and not justification:
            raise ValueError("A governance exception requires a justification.")
        exception = GovernanceException(
            id=f"exc_{uuid.uuid4().hex[:10]}",
            name=name,
            justification=justification,
            scope=scope or ExceptionScope(),
            granted_by=granted_by,
            expires_at=expires_at
            or datetime.now(timezone.utc) + timedelta(days=7),
            audit_ref="",
        )
        if max_uses is not None:
            exception.scope.max_uses = max_uses
        if environment is not None:
            exception.scope.environment = environment
        self._exceptions[exception.id] = exception
        return exception

    def get(self, exception_id: str) -> GovernanceException:
        return self._exceptions[exception_id]

    def revoke(self, exception_id: str) -> GovernanceException:
        exception = self._exceptions[exception_id]
        exception.status = ExceptionStatus.REVOKED
        return exception

    def applicable_to(
        self,
        request: GovernanceEvaluationRequest,
        *,
        rule_ids: Optional[set[str]] = None,
    ) -> List[GovernanceException]:
        """Active, unexpired, unrevoked exceptions whose scope covers the
        request. Order is deterministic (by id)."""
        now = datetime.now(timezone.utc)
        matches: List[GovernanceException] = []
        for exception in sorted(self._exceptions.values(), key=lambda e: e.id):
            if exception.status is ExceptionStatus.REVOKED:
                continue
            if exception.expires_at <= now:
                if exception.status is ExceptionStatus.ACTIVE:
                    exception.status = ExceptionStatus.EXPIRED
                continue
            if not exception.scope.covers(request):
                continue
            if (
                exception.scope.max_uses is not None
                and exception.use_count >= exception.scope.max_uses
            ):
                continue
            matches.append(exception)
        return matches

    def record_use(self, exception_id: str) -> None:
        self._exceptions[exception_id].use_count += 1

    def all(self) -> List[GovernanceException]:
        return sorted(self._exceptions.values(), key=lambda e: e.id)
