"""API authentication/actor dependencies.

Deployment assumption (explicit): read paths trust self-declared actor
headers and are suitable only behind a trusted boundary (loopback or an
authenticating proxy). All write paths (event ingest, commands) require
the shared token plus an authorized role. Actor identity itself is never
used as evidence of authority beyond these checks.
"""
from __future__ import annotations

from typing import Optional

from fastapi import Depends, Header, HTTPException, Request

from ..config import get_settings
from ..domain import Actor


def get_gateway(request: Request):
    return request.app.state.gateway


def get_actor(
    x_actor_id: Optional[str] = Header(default=None),
    x_actor_role: Optional[str] = Header(default=None),
    x_actor_clearance: Optional[str] = Header(default=None),
) -> Actor:
    return Actor(
        id=x_actor_id or "anonymous",
        role=x_actor_role or "observer",
        clearance=x_actor_clearance or x_actor_role or "observer",
    )


def require_writer(
    actor: Actor = Depends(get_actor),
    x_observatory_token: Optional[str] = Header(default=None),
) -> Actor:
    settings = get_settings()
    if settings.api_token and x_observatory_token != settings.api_token:
        raise HTTPException(status_code=401, detail="invalid observatory token")
    if actor.role not in {"operator", "architect", "admin", "system"}:
        raise HTTPException(status_code=403, detail="writer role required")
    return actor


def require_operator(
    actor: Actor = Depends(get_actor),
    x_observatory_token: Optional[str] = Header(default=None),
) -> Actor:
    settings = get_settings()
    if settings.api_token and x_observatory_token != settings.api_token:
        raise HTTPException(status_code=401, detail="invalid observatory token")
    clearance = actor.clearance or actor.role
    if clearance not in {"operator", "architect", "admin"}:
        raise HTTPException(status_code=403, detail="operator clearance required")
    return actor
