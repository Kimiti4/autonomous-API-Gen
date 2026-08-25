"""Capability grants — least-privilege authorization model."""
from __future__ import annotations
from enum import Enum
from typing import Optional, Sequence
from pydantic import BaseModel, ConfigDict, Field


class Capability(str, Enum):
    ISR_READ = "isr:read"
    ISR_WRITE = "isr:write"
    EVOLUTION_EXECUTE = "evolution:execute"
    COMPILER_EXECUTE = "compiler:execute"
    DEPLOYMENT_EXECUTE = "deployment:execute"
    GITHUB_REPOSITORY_CREATE = "github:repository:create"
    GITHUB_REPOSITORY_PUSH = "github:repository:push"
    IDENTITY_ADMIN = "identity:admin"


class CapabilityGrant(BaseModel):
    model_config = ConfigDict(frozen=True)

    grant_id: str = Field(min_length=1)
    principal_id: str = Field(min_length=1)
    capability: Capability
    scope: str = ""
    granted_at: str = ""
    expires_at: str | None = None


class GrantDecision(BaseModel):
    model_config = ConfigDict(frozen=True)

    authorized: bool = False
    grant_id: str | None = None
    reason: str = ""


class AuthorizationPort:
    """Technology-independent authorization seam."""

    def __init__(self, grants: Sequence[CapabilityGrant] | None = None) -> None:
        self._grants = list(grants or [])

    async def authorize(self, principal_id: str, capability: Capability, scope: str | None = None) -> GrantDecision:
        for g in self._grants:
            if g.principal_id != principal_id:
                continue
            if g.capability != capability:
                continue
            if g.scope and scope and not _scope_matches(g.scope, scope):
                continue
            return GrantDecision(authorized=True, grant_id=g.grant_id)
        return GrantDecision(authorized=False, reason="no_matching_grant")


class ReferenceAuthorizationPort(AuthorizationPort):
    """Reference adapter: in-memory grant list."""
    pass


def _scope_matches(granted: str, requested: str) -> bool:
    if granted.endswith("*"):
        return requested.startswith(granted[:-1])
    return granted == requested
