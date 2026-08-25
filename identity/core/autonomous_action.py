"""AutonomousActionRecord — audit trail for autonomous actions."""
from __future__ import annotations
from pydantic import BaseModel, ConfigDict


class AutonomousActionRecord(BaseModel):
    model_config = ConfigDict(frozen=True)

    action_id: str
    actor: str
    principal_id: str
    capability: str
    authorization_decision: str
    intent: str = ""
    isr_revision_id: str | None = None
    target: str = ""
    result: str = ""
    timestamp: str = ""
