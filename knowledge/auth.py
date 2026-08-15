"""
Actor and role model for the Knowledge Graph API.

This is intentionally simple and replaceable.

Production deployments should integrate the platform identity provider
and Phase 28 governance authorization model.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import Header, HTTPException
from pydantic import BaseModel, Field


class Actor(BaseModel):
    """An authenticated actor making a Knowledge Graph request."""

    actor_id: str
    roles: list[str] = Field(default_factory=list)

    def has_role(self, role: str) -> bool:
        return role in self.roles


def get_actor(
    x_actor_id: Annotated[str, Header(alias="X-Actor-Id")],
    x_actor_roles: Annotated[str, Header(alias="X-Actor-Roles")] = "",
) -> Actor:
    """
    Extract actor information from request headers.

    Replace this with real platform authentication in production.
    """
    roles = [role.strip() for role in x_actor_roles.split(",") if role.strip()]

    return Actor(
        actor_id=x_actor_id,
        roles=roles,
    )


def require_role(actor: Actor, role: str) -> None:
    """Fail closed if the actor does not have the required role."""
    if not actor.has_role(role):
        raise HTTPException(
            status_code=403,
            detail=f"Required role: {role}",
        )
