"""Workspace HTTP boundary: CRUD + export + audit over governed service.

 Disabled by default (403 workspaces_disabled). Operator identity is
 required; token enforcement follows OBSERVATORY_API_TOKEN presence with
 an explicit insecure-local escape hatch. All errors map to stable codes.
"""
from __future__ import annotations

import asyncio
import os
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from .workspace_governance import WorkspaceGovernor
from .workspace_governance_service import GovernedWorkspaceService
from .workspace_governance_store import WorkspaceGovernanceStore
from .workspace_service import WorkspaceService, WorkspaceRequestValidationError
from .workspaces_store import (
    SqliteWorkspaceStore,
    WorkspaceNotFound,
    WorkspacePermissionDenied,
)

router = APIRouter(prefix="/observatory/workspaces", tags=["workspaces"])


class WorkspaceQueryModel(BaseModel):
    q: Optional[str] = None
    categories: Optional[List[str]] = None
    severities: Optional[List[str]] = None
    epistemic_statuses: Optional[List[str]] = None
    since: Optional[str] = None
    until: Optional[str] = None
    limit: int = 200


class WorkspaceCreateRequest(BaseModel):
    name: str
    description: Optional[str] = ""
    query: WorkspaceQueryModel
    visibility: Optional[str] = "private"
    shared_with: Optional[List[str]] = Field(default_factory=list)
    tags: Optional[List[str]] = Field(default_factory=list)


class WorkspaceUpdateRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    query: Optional[WorkspaceQueryModel] = None
    visibility: Optional[str] = None
    shared_with: Optional[List[str]] = None
    tags: Optional[List[str]] = None


class RoleGrantRequest(BaseModel):
    operator_id: str
    role: str


def workspaces_enabled() -> bool:
    return os.getenv("OBSERVATORY_WORKSPACES_ENABLED",
                     "false").strip().lower() == "true"


def allow_insecure_local() -> bool:
    return os.getenv("OBSERVATORY_WORKSPACES_ALLOW_INSECURE_LOCAL",
                     "false").strip().lower() == "true"


def require_workspace_actor(request: Request) -> dict:
    if not workspaces_enabled():
        raise HTTPException(status_code=403, detail="workspaces_disabled")
    actor_id = request.headers.get("x-operator-id") or request.headers.get(
        "x-actor-id")
    role = (request.headers.get("x-operator-role")
            or request.headers.get("x-actor-role") or "observer")
    clearance = (request.headers.get("x-operator-clearance")
                 or request.headers.get("x-actor-clearance") or role)
    if not actor_id:
        raise HTTPException(status_code=401, detail="operator_id_required")
    token = request.headers.get("x-observatory-token")
    expected_token = os.getenv("OBSERVATORY_API_TOKEN")
    if expected_token:
        if token != expected_token:
            raise HTTPException(status_code=401, detail="invalid_token")
    elif not allow_insecure_local():
        raise HTTPException(status_code=403,
                            detail="workspace_auth_not_configured")
    roles_header = request.headers.get("x-operator-roles", "")
    roles = [item.strip() for item in roles_header.split(",") if item.strip()]
    if not roles:
        roles = [role]
    return {"id": actor_id, "role": role, "clearance": clearance,
            "roles": roles, "auth_method": "trusted-proxy"}


def get_workspace_service(request: Request) -> GovernedWorkspaceService:
    workspace_store: SqliteWorkspaceStore = request.app.state.workspace_store
    governance_store = request.app.state.workspace_governance_store
    event_store = request.app.state.gateway.store
    base_service = WorkspaceService(workspace_store, event_store)
    governor = WorkspaceGovernor()
    return GovernedWorkspaceService(base_service, governance_store, governor)


@router.post("")
async def create_workspace(
    payload: WorkspaceCreateRequest,
    actor: dict = Depends(require_workspace_actor),
    service: GovernedWorkspaceService = Depends(get_workspace_service),
):
    try:
        return await asyncio.to_thread(
            service.create_workspace, actor, payload.model_dump())
    except WorkspaceRequestValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except WorkspacePermissionDenied as exc:
        raise HTTPException(status_code=403,
                            detail="workspace_access_denied") from exc


@router.get("")
async def list_workspaces(
    actor: dict = Depends(require_workspace_actor),
    service: GovernedWorkspaceService = Depends(get_workspace_service),
):
    return await asyncio.to_thread(service.list_workspaces, actor)


@router.get("/{workspace_id}")
async def get_workspace(
    workspace_id: str,
    actor: dict = Depends(require_workspace_actor),
    service: GovernedWorkspaceService = Depends(get_workspace_service),
):
    try:
        return await asyncio.to_thread(
            service.get_workspace, actor, workspace_id)
    except WorkspaceNotFound as exc:
        raise HTTPException(status_code=404,
                            detail="workspace_not_found") from exc
    except WorkspacePermissionDenied as exc:
        raise HTTPException(status_code=403,
                            detail="workspace_access_denied") from exc


@router.put("/{workspace_id}")
async def update_workspace(
    workspace_id: str,
    payload: WorkspaceUpdateRequest,
    actor: dict = Depends(require_workspace_actor),
    service: GovernedWorkspaceService = Depends(get_workspace_service),
):
    try:
        return await asyncio.to_thread(
            service.update_workspace, actor, workspace_id,
            payload.model_dump(exclude_unset=True))
    except WorkspaceNotFound as exc:
        raise HTTPException(status_code=404,
                            detail="workspace_not_found") from exc
    except WorkspacePermissionDenied as exc:
        raise HTTPException(status_code=403,
                            detail="workspace_access_denied") from exc
    except WorkspaceRequestValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.delete("/{workspace_id}")
async def delete_workspace(
    workspace_id: str,
    actor: dict = Depends(require_workspace_actor),
    service: GovernedWorkspaceService = Depends(get_workspace_service),
):
    try:
        deleted = await asyncio.to_thread(
            service.delete_workspace, actor, workspace_id)
        return {"status": "deleted", "workspace_id": deleted["id"]}
    except WorkspaceNotFound as exc:
        raise HTTPException(status_code=404,
                            detail="workspace_not_found") from exc
    except WorkspacePermissionDenied as exc:
        raise HTTPException(status_code=403,
                            detail="workspace_access_denied") from exc


@router.get("/{workspace_id}/export")
async def export_workspace(
    workspace_id: str,
    actor: dict = Depends(require_workspace_actor),
    service: GovernedWorkspaceService = Depends(get_workspace_service),
):
    try:
        return await asyncio.to_thread(
            service.export_workspace, actor, workspace_id)
    except WorkspaceNotFound as exc:
        raise HTTPException(status_code=404,
                            detail="workspace_not_found") from exc
    except WorkspacePermissionDenied as exc:
        raise HTTPException(status_code=403,
                            detail="workspace_access_denied") from exc


@router.get("/{workspace_id}/audit")
async def get_workspace_audit(
    workspace_id: str,
    limit: int = 200,
    actor: dict = Depends(require_workspace_actor),
    service: GovernedWorkspaceService = Depends(get_workspace_service),
):
    try:
        return await asyncio.to_thread(
            service.get_audit, actor, workspace_id, limit)
    except WorkspaceNotFound as exc:
        raise HTTPException(status_code=404,
                            detail="workspace_not_found") from exc
    except WorkspacePermissionDenied as exc:
        raise HTTPException(status_code=403,
                            detail="workspace_access_denied") from exc


@router.post("/{workspace_id}/roles")
async def grant_workspace_role(
    workspace_id: str,
    payload: RoleGrantRequest,
    actor: dict = Depends(require_workspace_actor),
    service: GovernedWorkspaceService = Depends(get_workspace_service),
):
    try:
        return await asyncio.to_thread(
            service.grant_role, actor, workspace_id, payload.operator_id,
            payload.role)
    except WorkspaceNotFound as exc:
        raise HTTPException(status_code=404,
                            detail="workspace_not_found") from exc
    except WorkspacePermissionDenied as exc:
        raise HTTPException(status_code=403,
                            detail="workspace_access_denied") from exc
    except WorkspaceRequestValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.delete("/{workspace_id}/roles/{operator_id}")
async def revoke_workspace_role(
    workspace_id: str,
    operator_id: str,
    actor: dict = Depends(require_workspace_actor),
    service: GovernedWorkspaceService = Depends(get_workspace_service),
):
    try:
        return await asyncio.to_thread(
            service.revoke_role, actor, workspace_id, operator_id)
    except WorkspaceNotFound as exc:
        raise HTTPException(status_code=404,
                            detail="workspace_not_found") from exc
    except WorkspacePermissionDenied as exc:
        raise HTTPException(status_code=403,
                            detail="workspace_access_denied") from exc
    except WorkspaceRequestValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
