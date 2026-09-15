"""VS-D25 — TaskV3Repository: persistence adapter for priority tasks.

The v1 TaskTrackerStore task methods construct the v1 Task type, which
cannot hold priority, and the parent store must not be modified. This
adapter therefore operates on the store's state mapping for task records
only, reusing the store's atomic persistence. Users, workspaces,
memberships, sessions, events, and counters all go through the parent
store's public API unchanged.

Dependence is on the storage-record shape (documented in
vertical_slice/app/store.py), never on parent task behavior.
"""

from __future__ import annotations

from dataclasses import asdict
from typing import Any

from vertical_slice.app.store import TaskTrackerStore
from vertical_slice.app_v3.models import TaskV3
from vertical_slice.app_v3.policy import PriorityQueryPolicy


class TaskV3Repository:
    """Priority-task persistence over a shared TaskTrackerStore."""

    def __init__(self, store: TaskTrackerStore,
                 policy: PriorityQueryPolicy | None = None) -> None:
        self._store = store
        self._policy = policy or PriorityQueryPolicy()

    def _tasks(self) -> dict[str, Any]:
        state = self._store._state  # adapter seam; see module docstring
        return state.setdefault("tasks", {})

    def _persist(self) -> None:
        self._store._persist()  # atomic write-temp-then-replace, as v1

    def put(self, task: TaskV3) -> None:
        self._tasks()[task.task_id] = asdict(task)
        self._persist()

    def get(self, task_id: str) -> TaskV3 | None:
        raw = self._tasks().get(task_id)
        if raw is None:
            return None
        return TaskV3(**self._policy.apply_legacy_default(dict(raw)))

    def delete(self, task_id: str) -> bool:
        if task_id not in self._tasks():
            return False
        del self._tasks()[task_id]
        self._persist()
        return True

    def list_in_workspace(self, workspace_id: str) -> list[TaskV3]:
        return sorted(
            (TaskV3(**self._policy.apply_legacy_default(dict(raw)))
             for raw in self._tasks().values()
             if raw.get("workspace_id") == workspace_id),
            key=lambda t: t.task_id,
        )
