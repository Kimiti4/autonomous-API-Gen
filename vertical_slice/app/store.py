"""VS-D04 — durable JSON-file repository (supports req-durability).

Deterministic serialization: sorted keys, compact separators, UTF-8.
All writes are atomic (write-temp-then-replace) so committed state survives
process restarts. No backend/framework dependencies.
"""

from __future__ import annotations

import json
import os
from dataclasses import asdict

from vertical_slice.app.models import DomainEvent, Membership, Session, Task, User, Workspace

_STATE_FILE = "store.json"


def _dump(state: dict[str, object]) -> str:
    return json.dumps(state, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


class TaskTrackerStore:
    """File-backed repository rooted at a directory."""

    def __init__(self, root: str) -> None:
        self._root = root
        self._path = os.path.join(root, _STATE_FILE)
        os.makedirs(root, exist_ok=True)
        if os.path.exists(self._path):
            with open(self._path, encoding="utf-8") as f:
                self._state: dict[str, object] = json.load(f)
        else:
            self._state = {
                "users": {}, "workspaces": {}, "memberships": [],
                "tasks": {}, "events": [], "sessions": {},
                "counters": {"user": 0, "task": 0, "event": 0},
            }
            self._persist()

    def _persist(self) -> None:
        tmp = self._path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            f.write(_dump(self._state))
        os.replace(tmp, self._path)

    def raw_bytes(self) -> bytes:
        with open(self._path, "rb") as f:
            return f.read()

    # -- ids (deterministic counters; no randomness in identity) -------------
    def next_user_id(self) -> str:
        self._state["counters"]["user"] += 1
        self._persist()
        return f"user-{self._state['counters']['user']:04d}"

    def next_task_id(self) -> str:
        self._state["counters"]["task"] += 1
        self._persist()
        return f"task-{self._state['counters']['task']:04d}"

    def next_event_id(self) -> str:
        self._state["counters"]["event"] += 1
        self._persist()
        return f"event-{self._state['counters']['event']:04d}"

    # -- users ------------------------------------------------------------------
    def put_user(self, user: User) -> None:
        self._state["users"][user.user_id] = asdict(user)
        self._persist()

    def find_user_by_name(self, username: str) -> User | None:
        for raw in self._state["users"].values():
            if raw["username"] == username:
                return User(**raw)
        return None

    def get_user(self, user_id: str) -> User | None:
        raw = self._state["users"].get(user_id)
        return User(**raw) if raw is not None else None

    # -- workspaces / membership --------------------------------------------------
    def put_workspace(self, workspace: Workspace) -> None:
        self._state["workspaces"][workspace.workspace_id] = asdict(workspace)
        self._persist()

    def get_workspace(self, workspace_id: str) -> Workspace | None:
        raw = self._state["workspaces"].get(workspace_id)
        return Workspace(**raw) if raw is not None else None

    def put_membership(self, membership: Membership) -> None:
        members = [m for m in self._state["memberships"]
                   if not (m["workspace_id"] == membership.workspace_id
                           and m["user_id"] == membership.user_id)]
        members.append(asdict(membership))
        self._state["memberships"] = members
        self._persist()

    def remove_membership(self, workspace_id: str, user_id: str) -> bool:
        before = len(self._state["memberships"])
        self._state["memberships"] = [
            m for m in self._state["memberships"]
            if not (m["workspace_id"] == workspace_id and m["user_id"] == user_id)]
        removed = len(self._state["memberships"]) != before
        if removed:
            self._persist()
        return removed

    def membership(self, workspace_id: str, user_id: str) -> Membership | None:
        for raw in self._state["memberships"]:
            if raw["workspace_id"] == workspace_id and raw["user_id"] == user_id:
                return Membership(**raw)
        return None

    def ensure_workspace(self, workspace_id: str, name: str) -> Workspace:
        """Test/setup scaffolding: workspaces have no create-capability in the
        ISR, so tests seed them explicitly through this documented helper."""
        existing = self.get_workspace(workspace_id)
        if existing is not None:
            return existing
        workspace = Workspace(workspace_id=workspace_id, name=name)
        self.put_workspace(workspace)
        return workspace

    # -- tasks -----------------------------------------------------------------------
    def put_task(self, task: Task) -> None:
        self._state["tasks"][task.task_id] = asdict(task)
        self._persist()

    def get_task(self, task_id: str) -> Task | None:
        raw = self._state["tasks"].get(task_id)
        return Task(**raw) if raw is not None else None

    def delete_task(self, task_id: str) -> bool:
        if task_id not in self._state["tasks"]:
            return False
        del self._state["tasks"][task_id]
        self._persist()
        return True

    def tasks_in_workspace(self, workspace_id: str) -> list[Task]:
        return sorted(
            (Task(**raw) for raw in self._state["tasks"].values()
             if raw["workspace_id"] == workspace_id),
            key=lambda t: t.task_id,
        )

    # -- events ------------------------------------------------------------------------
    def append_event(self, event: DomainEvent) -> None:
        self._state["events"].append(asdict(event))
        self._persist()

    def events_for_task(self, task_id: str) -> list[DomainEvent]:
        return [DomainEvent(**raw) for raw in self._state["events"]
                if raw["task_id"] == task_id]

    # -- sessions -------------------------------------------------------------------------
    def put_session(self, session: Session) -> None:
        self._state["sessions"][session.token] = asdict(session)
        self._persist()

    def get_session(self, token: str) -> Session | None:
        raw = self._state["sessions"].get(token)
        return Session(**raw) if raw is not None else None

    def drop_session(self, token: str) -> None:
        if token in self._state["sessions"]:
            del self._state["sessions"][token]
            self._persist()
