"""Authorization service — authorize + emit AutonomousActionRecord."""
from __future__ import annotations
import uuid
from identity.capabilities.grants import AuthorizationPort, Capability, GrantDecision
from identity.core.autonomous_action import AutonomousActionRecord


class AuthorizationService:
    """Authorize + emit an AutonomousActionRecord feeding v1.1 accountability."""

    def __init__(self, authz: AuthorizationPort) -> None:
        self._authz = authz

    async def authorize_and_record(
        self,
        principal_id: str,
        capability: Capability,
        scope: str | None = None,
        intent: str = "",
        isr_revision_id: str | None = None,
        target: str = "",
    ) -> tuple[GrantDecision, AutonomousActionRecord]:
        decision = await self._authz.authorize(principal_id, capability, scope)
        rec = AutonomousActionRecord(
            action_id=str(uuid.uuid4()),
            actor=f"principal:{principal_id}",
            principal_id=principal_id,
            capability=capability.value,
            authorization_decision=decision.grant_id or "denied",
            intent=intent,
            isr_revision_id=isr_revision_id,
            target=target,
            result="authorized" if decision.authorized else "denied",
            timestamp="",
        )
        return decision, rec
