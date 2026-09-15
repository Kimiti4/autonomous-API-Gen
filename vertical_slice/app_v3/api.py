"""VS-D25 — product interface layer for VS1-OBJ-001.

Same route contract as app_v2 plus the priority capability: create/update
accept priority, reads serialize it, and listing accepts ?priority= with
fail-closed validation. Wired to TaskTrackerServiceV3. No server here.
"""

from __future__ import annotations

from typing import Callable

from fastapi import Depends, FastAPI, Header, HTTPException, Query
from pydantic import BaseModel, Field

from vertical_slice.app.service import _UNSET
from vertical_slice.app_v3.service import (
    AuthError,
    AuthorizationError,
    TaskTrackerServiceV3,
    ValidationError,
)
from vertical_slice.app.store import TaskTrackerStore


class RegisterBody(BaseModel):
    username: str = Field(min_length=1)
    password: str = Field(min_length=1)


class LoginBody(BaseModel):
    username: str = Field(min_length=1)
    password: str = Field(min_length=1)


class TaskCreateBody(BaseModel):
    title: str = Field(min_length=1)
    status: str = Field(default="open", min_length=1)
    priority: str = Field(default="MEDIUM", min_length=1)


class TaskUpdateBody(BaseModel):
    title: str | None = Field(default=None, min_length=1)
    status: str | None = Field(default=None, min_length=1)
    assignee_id: str | None = None
    priority: str | None = Field(default=None, min_length=1)


class MemberBody(BaseModel):
    user_id: str = Field(min_length=1)
    role: str = Field(default="member")


def _http_error(exc: Exception) -> HTTPException:
    if isinstance(exc, AuthError):
        return HTTPException(status_code=401, detail=str(exc))
    if isinstance(exc, AuthorizationError):
        return HTTPException(status_code=403, detail=str(exc))
    return HTTPException(status_code=422, detail=str(exc))


def create_app(store: TaskTrackerStore,
               token_generator: Callable[[], str] | None = None) -> FastAPI:
    service = TaskTrackerServiceV3(store, token_generator=token_generator)
    app = FastAPI(title="vs1-task-tracker-v3")

    def _token(authorization: str | None = Header(default=None)) -> str:
        if not authorization or not authorization.startswith("Bearer "):
            raise HTTPException(status_code=401, detail="invalid credentials")
        return authorization[len("Bearer "):]

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.post("/users/register", status_code=201)
    def register(body: RegisterBody) -> dict[str, str]:
        try:
            user = service.register(body.username, body.password)
        except (ValidationError, AuthError, AuthorizationError) as exc:
            raise _http_error(exc)
        return {"user_id": user.user_id}

    @app.post("/users/login")
    def login(body: LoginBody) -> dict[str, str]:
        try:
            token = service.login(body.username, body.password)
        except (ValidationError, AuthError, AuthorizationError) as exc:
            raise _http_error(exc)
        return {"token": token}

    @app.post("/workspaces/{workspace_id}/tasks", status_code=201)
    def create_task(workspace_id: str, body: TaskCreateBody,
                    token: str = Depends(_token)) -> dict[str, object]:
        try:
            task = service.create_task(token, workspace_id, body.title,
                                       body.status, body.priority)
        except (ValidationError, AuthError, AuthorizationError) as exc:
            raise _http_error(exc)
        return _task_json(task)

    @app.get("/workspaces/{workspace_id}/tasks")
    def list_tasks(workspace_id: str, token: str = Depends(_token),
                   priority: str | None = Query(default=None)
                   ) -> list[dict[str, object]]:
        try:
            tasks = service.list_tasks(token, workspace_id, priority)
        except (ValidationError, AuthError, AuthorizationError) as exc:
            raise _http_error(exc)
        return [_task_json(task) for task in tasks]

    @app.get("/workspaces/{workspace_id}/tasks/{task_id}")
    def get_task(workspace_id: str, task_id: str,
                 token: str = Depends(_token)) -> dict[str, object]:
        try:
            task = service.get_task(token, task_id)
        except (ValidationError, AuthError, AuthorizationError) as exc:
            raise _http_error(exc)
        if task.workspace_id != workspace_id:
            raise HTTPException(status_code=403, detail="caller is not a workspace member")
        return _task_json(task)

    @app.patch("/workspaces/{workspace_id}/tasks/{task_id}")
    def update_task(workspace_id: str, task_id: str, body: TaskUpdateBody,
                    token: str = Depends(_token)) -> dict[str, object]:
        try:
            assignee = (body.assignee_id if "assignee_id" in body.model_fields_set
                        else _UNSET)
            priority = (body.priority if "priority" in body.model_fields_set
                        else _UNSET)
            task = service.update_task(token, task_id, title=body.title,
                                       status=body.status,
                                       assignee_id=assignee, priority=priority)
        except (ValidationError, AuthError, AuthorizationError) as exc:
            raise _http_error(exc)
        if task.workspace_id != workspace_id:
            raise HTTPException(status_code=403, detail="caller is not a workspace member")
        return _task_json(task)

    @app.delete("/workspaces/{workspace_id}/tasks/{task_id}", status_code=204)
    def delete_task(workspace_id: str, task_id: str,
                    token: str = Depends(_token)) -> None:
        try:
            task = service.get_task(token, task_id)
        except (ValidationError, AuthError, AuthorizationError) as exc:
            raise _http_error(exc)
        if task.workspace_id != workspace_id:
            raise HTTPException(status_code=403, detail="caller is not a workspace member")
        try:
            service.delete_task(token, task_id)
        except (ValidationError, AuthError, AuthorizationError) as exc:
            raise _http_error(exc)

    @app.post("/workspaces/{workspace_id}/members", status_code=201)
    def add_member(workspace_id: str, body: MemberBody,
                   token: str = Depends(_token)) -> dict[str, str]:
        try:
            membership = service.add_member(token, workspace_id, body.user_id, body.role)
        except (ValidationError, AuthError, AuthorizationError) as exc:
            raise _http_error(exc)
        return {"workspace_id": membership.workspace_id,
                "user_id": membership.user_id, "role": membership.role}

    @app.delete("/workspaces/{workspace_id}/members/{user_id}", status_code=204)
    def remove_member(workspace_id: str, user_id: str,
                      token: str = Depends(_token)) -> None:
        try:
            service.remove_member(token, workspace_id, user_id)
        except (ValidationError, AuthError, AuthorizationError) as exc:
            raise _http_error(exc)

    return app


def _task_json(task) -> dict[str, object]:
    return {
        "task_id": task.task_id,
        "workspace_id": task.workspace_id,
        "title": task.title,
        "status": task.status,
        "owner_id": task.owner_id,
        "assignee_id": task.assignee_id,
        "priority": task.priority,
    }
