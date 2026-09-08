"""VS-D15 — domain service layer, central-policy profile.

Identical behavior to vertical_slice.app.service; every authorization
decision is delegated to AuthorizationPolicy (the evolved boundary).
"""

from __future__ import annotations

from typing import Callable

from vertical_slice.app.models import DomainEvent, Membership, Session, Task, User
from vertical_slice.app.security import hash_password, new_salt, verify_password
from vertical_slice.app.store import TaskTrackerStore
from vertical_slice.app_v2.policy import AuthorizationPolicy
from vertical_slice.app.service import (
    AuthError,
    AuthorizationError,
    ValidationError,
    _UNSET,
)

__all__ = [
    "AuthError",
    "AuthorizationError",
    "ValidationError",
    "TaskTrackerServiceV2",
]


class TaskTrackerServiceV2:
    def __init__(self, store: TaskTrackerStore,
                 token_generator: Callable[[], str] | None = None,
                 random_bytes=None) -> None:
        self._store = store
        self._policy = AuthorizationPolicy(store)
        self._token_generator = token_generator
        self._random_bytes = random_bytes
        self._token_counter = 0

    def _issue_token(self) -> str:
        if self._token_generator is not None:
            return self._token_generator()
        self._token_counter += 1
        return f"test-token-{self._token_counter:04d}"

    @staticmethod
    def _require_non_empty(value: str, field: str) -> str:
        cleaned = value.strip() if isinstance(value, str) else ""
        if not cleaned:
            raise ValidationError(f"{field} must be a non-empty string")
        return cleaned

    # -- identity (svc-identity) ----------------------------------------------
    def register(self, username: str, password: str) -> User:
        username = self._require_non_empty(username, "username")
        password = self._require_non_empty(password, "password")
        if self._store.find_user_by_name(username) is not None:
            raise ValidationError("identity already exists")
        salt = new_salt() if self._random_bytes is None else new_salt(self._random_bytes)
        user = User(
            user_id=self._store.next_user_id(),
            username=username,
            password_hash=hash_password(password, salt),
            salt_hex=salt,
        )
        self._store.put_user(user)
        return user

    def login(self, username: str, password: str) -> str:
        user = self._store.find_user_by_name(username.strip() if isinstance(username, str) else "")
        if user is None or not verify_password(password or "", user.salt_hex, user.password_hash):
            raise AuthError("invalid credentials")
        token = self._issue_token()
        self._store.put_session(Session(token=token, user_id=user.user_id))
        return token

    # -- tasks (svc-task) -------------------------------------------------------
    def create_task(self, token: str, workspace_id: str, title: str,
                    status: str = "open") -> Task:
        user = self._policy.check_session(token)
        self._policy.check_member(workspace_id, user.user_id)
        title = self._require_non_empty(title, "title")
        status = self._require_non_empty(status, "status")
        task = Task(
            task_id=self._store.next_task_id(),
            workspace_id=workspace_id,
            title=title,
            status=status,
            owner_id=user.user_id,
        )
        self._store.put_task(task)
        self._store.append_event(DomainEvent(
            event_id=self._store.next_event_id(),
            event_name="task-created",
            task_id=task.task_id,
            producer="svc-task",
            payload={"title": title, "status": status, "owner_id": user.user_id},
        ))
        return task

    def list_tasks(self, token: str, workspace_id: str) -> list[Task]:
        user = self._policy.check_session(token)
        self._policy.check_member(workspace_id, user.user_id)
        return self._store.tasks_in_workspace(workspace_id)

    def get_task(self, token: str, task_id: str) -> Task:
        user = self._policy.check_session(token)
        task = self._store.get_task(task_id)
        if task is None:
            raise ValidationError("unknown task")
        self._policy.check_member(task.workspace_id, user.user_id)
        return task

    def update_task(self, token: str, task_id: str, title: str | None = None,
                    status: str | None = None, assignee_id: object = _UNSET) -> Task:
        user = self._policy.check_session(token)
        task = self._store.get_task(task_id)
        if task is None:
            raise ValidationError("unknown task")
        self._policy.check_member(task.workspace_id, user.user_id)
        new_title = task.title if title is None else self._require_non_empty(title, "title")
        new_status = task.status if status is None else self._require_non_empty(status, "status")
        new_assignee = task.assignee_id
        if assignee_id is not _UNSET:
            if assignee_id is not None and self._store.membership(
                    task.workspace_id, assignee_id) is None:
                raise ValidationError("assignee is not a workspace member")
            new_assignee = assignee_id
        updated = Task(
            task_id=task.task_id, workspace_id=task.workspace_id,
            title=new_title, status=new_status, owner_id=task.owner_id,
            assignee_id=new_assignee,
        )
        self._store.put_task(updated)
        self._store.append_event(DomainEvent(
            event_id=self._store.next_event_id(),
            event_name="task-updated",
            task_id=task.task_id,
            producer="svc-task",
            payload={"title": new_title, "status": new_status,
                     "assignee_id": new_assignee},
        ))
        return updated

    def assign_task(self, token: str, task_id: str, assignee_id: str) -> Task:
        return self.update_task(token, task_id, assignee_id=assignee_id)

    def delete_task(self, token: str, task_id: str) -> None:
        user = self._policy.check_session(token)
        task = self._store.get_task(task_id)
        if task is None:
            raise ValidationError("unknown task")
        self._policy.check_member(task.workspace_id, user.user_id)
        self._store.delete_task(task_id)

    def events_for_task(self, token: str, task_id: str) -> list[DomainEvent]:
        task = self.get_task(token, task_id)
        return self._store.events_for_task(task.task_id)

    # -- membership (svc-workspace, admin-only) -----------------------------------
    def add_member(self, token: str, workspace_id: str, user_id: str,
                   role: str = "member") -> Membership:
        user = self._policy.check_session(token)
        self._policy.check_admin(workspace_id, user.user_id)
        if role not in ("admin", "member"):
            raise ValidationError("unknown role")
        if self._store.get_user(user_id) is None:
            raise ValidationError("unknown user")
        membership = Membership(workspace_id=workspace_id, user_id=user_id, role=role)
        self._store.put_membership(membership)
        return membership

    def remove_member(self, token: str, workspace_id: str, user_id: str) -> None:
        user = self._policy.check_session(token)
        self._policy.check_admin(workspace_id, user.user_id)
        if not self._store.remove_membership(workspace_id, user_id):
            raise ValidationError("unknown membership")
