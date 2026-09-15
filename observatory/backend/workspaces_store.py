"""Workspace persistence: definitions plus append-only audit log.

Owner-controlled mutation is enforced one layer up (service/governor);
the store guarantees atomic writes and never silently drops audit rows.
"""
from __future__ import annotations

import json
import sqlite3
import threading
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


class WorkspaceNotFound(Exception):
    pass


class WorkspacePermissionDenied(Exception):
    pass


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def generate_workspace_id() -> str:
    return f"ws-{uuid.uuid4().hex[:16]}"


def generate_audit_id() -> str:
    return f"wsaud-{uuid.uuid4().hex[:16]}"


class SqliteWorkspaceStore:
    def __init__(self, db_path: str) -> None:
        self._db_path = db_path
        self._lock = threading.RLock()
        self._conn = sqlite3.connect(db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL;")
        self._conn.execute("PRAGMA synchronous=NORMAL;")

    def init(self) -> None:
        with self._lock:
            self._conn.execute(
                """
                CREATE TABLE IF NOT EXISTS workspaces (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    description TEXT NOT NULL,
                    owner_id TEXT NOT NULL,
                    visibility TEXT NOT NULL,
                    shared_with TEXT NOT NULL,
                    tags TEXT NOT NULL,
                    query TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    version INTEGER NOT NULL DEFAULT 1
                )
                """)
            self._conn.execute(
                "CREATE INDEX IF NOT EXISTS workspaces_owner_idx "
                "ON workspaces (owner_id)")
            self._conn.execute(
                """
                CREATE TABLE IF NOT EXISTS workspace_audit (
                    id TEXT PRIMARY KEY,
                    workspace_id TEXT NOT NULL,
                    actor_id TEXT NOT NULL,
                    action TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    details TEXT NOT NULL
                )
                """)
            self._conn.execute(
                "CREATE INDEX IF NOT EXISTS workspace_audit_workspace_idx "
                "ON workspace_audit (workspace_id, timestamp)")
            self._conn.commit()

    def close(self) -> None:
        with self._lock:
            self._conn.close()

    def create_workspace(self, workspace: Dict[str, Any]) -> Dict[str, Any]:
        with self._lock:
            self._conn.execute(
                """INSERT INTO workspaces (id, name, description, owner_id,
                    visibility, shared_with, tags, query, created_at,
                    updated_at, version)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (workspace["id"], workspace["name"],
                 workspace["description"], workspace["owner_id"],
                 workspace["visibility"],
                 json.dumps(workspace["shared_with"], sort_keys=True),
                 json.dumps(workspace["tags"], sort_keys=True),
                 json.dumps(workspace["query"], sort_keys=True),
                 workspace["created_at"], workspace["updated_at"],
                 workspace["version"]))
            self._conn.commit()
        return workspace

    def get_workspace(self, workspace_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            row = self._conn.execute(
                "SELECT * FROM workspaces WHERE id = ?",
                (workspace_id,)).fetchone()
        if row is None:
            return None
        return self._row_to_workspace(row)

    def list_workspaces(self) -> List[Dict[str, Any]]:
        with self._lock:
            rows = self._conn.execute(
                "SELECT * FROM workspaces ORDER BY updated_at DESC, id ASC"
            ).fetchall()
        return [self._row_to_workspace(row) for row in rows]

    def update_workspace(self, workspace_id: str, owner_id: str,
                         updates: Dict[str, Any]) -> Dict[str, Any]:
        with self._lock:
            row = self._conn.execute(
                "SELECT * FROM workspaces WHERE id = ?",
                (workspace_id,)).fetchone()
            if row is None:
                raise WorkspaceNotFound(workspace_id)
            current = self._row_to_workspace(row)
            if current["owner_id"] != owner_id:
                raise WorkspacePermissionDenied(workspace_id)
        return self.apply_update(workspace_id, updates)

    def apply_update(self, workspace_id: str,
                     updates: Dict[str, Any]) -> Dict[str, Any]:
        """Persistence-only update without an ownership check.

        Governed-only path: callers must have passed policy authorization
        (role-based mutation). The base service keeps its owner gate and
        delegates here after checking.
        """
        with self._lock:
            row = self._conn.execute(
                "SELECT * FROM workspaces WHERE id = ?",
                (workspace_id,)).fetchone()
            if row is None:
                raise WorkspaceNotFound(workspace_id)
            current = self._row_to_workspace(row)
            updated = dict(current)
            for key in ("name", "description", "visibility", "shared_with",
                        "tags", "query"):
                if key in updates:
                    updated[key] = updates[key]
            updated["updated_at"] = utc_now_iso()
            updated["version"] = current["version"] + 1
            self._conn.execute(
                """UPDATE workspaces SET name = ?, description = ?,
                    visibility = ?, shared_with = ?, tags = ?, query = ?,
                    updated_at = ?, version = ? WHERE id = ?""",
                (updated["name"], updated["description"],
                 updated["visibility"],
                 json.dumps(updated["shared_with"], sort_keys=True),
                 json.dumps(updated["tags"], sort_keys=True),
                 json.dumps(updated["query"], sort_keys=True),
                 updated["updated_at"], updated["version"], workspace_id))
            self._conn.commit()
        return updated

    def delete_workspace(self, workspace_id: str,
                         owner_id: str) -> Dict[str, Any]:
        with self._lock:
            row = self._conn.execute(
                "SELECT * FROM workspaces WHERE id = ?",
                (workspace_id,)).fetchone()
            if row is None:
                raise WorkspaceNotFound(workspace_id)
            workspace = self._row_to_workspace(row)
            if workspace["owner_id"] != owner_id:
                raise WorkspacePermissionDenied(workspace_id)
            self._conn.execute("DELETE FROM workspaces WHERE id = ?",
                               (workspace_id,))
            self._conn.commit()
        return workspace

    def add_audit(self, workspace_id: str, actor_id: str, action: str,
                  details: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        audit_record = {
            "id": generate_audit_id(), "workspace_id": workspace_id,
            "actor_id": actor_id, "action": action,
            "timestamp": utc_now_iso(), "details": details or {},
        }
        with self._lock:
            self._conn.execute(
                """INSERT INTO workspace_audit (id, workspace_id, actor_id,
                    action, timestamp, details)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (audit_record["id"], audit_record["workspace_id"],
                 audit_record["actor_id"], audit_record["action"],
                 audit_record["timestamp"],
                 json.dumps(audit_record["details"], sort_keys=True)))
            self._conn.commit()
        return audit_record

    def get_audit(self, workspace_id: str,
                  limit: int = 200) -> List[Dict[str, Any]]:
        with self._lock:
            rows = self._conn.execute(
                "SELECT * FROM workspace_audit WHERE workspace_id = ? "
                "ORDER BY timestamp DESC, id DESC LIMIT ?",
                (workspace_id, limit)).fetchall()
        return [self._row_to_audit(row) for row in rows]

    def _row_to_workspace(self, row: sqlite3.Row) -> Dict[str, Any]:
        return {
            "id": row["id"], "name": row["name"],
            "description": row["description"], "owner_id": row["owner_id"],
            "visibility": row["visibility"],
            "shared_with": json.loads(row["shared_with"]),
            "tags": json.loads(row["tags"]),
            "query": json.loads(row["query"]),
            "created_at": row["created_at"],
            "updated_at": row["updated_at"], "version": row["version"],
        }

    def _row_to_audit(self, row: sqlite3.Row) -> Dict[str, Any]:
        return {
            "id": row["id"], "workspace_id": row["workspace_id"],
            "actor_id": row["actor_id"], "action": row["action"],
            "timestamp": row["timestamp"],
            "details": json.loads(row["details"]),
        }
