"""VS-D25 — domain models for the priority capability.

Reuses every v1 model unchanged (User, Workspace, Membership, Session,
DomainEvent). Adds TaskV3: the v1 Task shape plus a closed priority
attribute. The parent app.models.Task is never modified.
"""

from __future__ import annotations

from dataclasses import dataclass

from vertical_slice.app.models import (  # noqa: F401  (re-exported)
    DomainEvent,
    Membership,
    Session,
    User,
    Workspace,
)

PRIORITY_VALUES: tuple[str, str, str] = ("LOW", "MEDIUM", "HIGH")
LEGACY_DEFAULT_PRIORITY = "MEDIUM"


@dataclass(frozen=True)
class TaskV3:
    """dm-task evolved for VS1-OBJ-001 (priority capability)."""

    task_id: str
    workspace_id: str
    title: str
    status: str
    owner_id: str
    assignee_id: str | None = None
    priority: str = LEGACY_DEFAULT_PRIORITY
