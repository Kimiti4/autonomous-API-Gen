"""VS-D04 — task-tracker domain models (selected: vs1-candidate-a).

Every type maps to a VS-D02 ISR node (see vertical_slice/implementation.py
COMPONENT_ISR_MAP). Plain dataclasses; no framework imports here.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class User:
    """dom-user-account."""

    user_id: str
    username: str
    password_hash: str
    salt_hex: str


@dataclass(frozen=True)
class Workspace:
    """dom-workspace."""

    workspace_id: str
    name: str


@dataclass(frozen=True)
class Membership:
    """Workspace membership + role (supports req-workspace-members)."""

    workspace_id: str
    user_id: str
    role: str  # "admin" or "member"


@dataclass(frozen=True)
class Task:
    """dom-task."""

    task_id: str
    workspace_id: str
    title: str
    status: str
    owner_id: str
    assignee_id: str | None = None


@dataclass(frozen=True)
class DomainEvent:
    """ev-task-created / ev-task-updated."""

    event_id: str
    event_name: str
    task_id: str
    producer: str
    payload: dict[str, object] = field(default_factory=dict)


@dataclass(frozen=True)
class Session:
    token: str
    user_id: str
