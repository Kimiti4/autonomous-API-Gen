"""Governance persistence: state, roles, immutable snapshots, hash-chained audit.

Snapshots and audit-chain rows link previous_hash → hash, so tampering
with history is detectable by recomputation. Close() releases the handle
(Windows file-lock hygiene, as with the event store).
"""
from __future__ import annotations

import json
import sqlite3
import threading
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from .workspace_governance import (
    ASSIGNABLE_WORKSPACE_ROLES,
    LIFECYCLE_STATES,
    SENSITIVITY_LEVELS,
    canonical_json,
    sha256_hex,
    workspace_governance_hash,
)


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def generate_snapshot_id() -> str:
    return f"wssnap-{uuid.uuid4().hex[:16]}"


def generate_audit_chain_id() -> str:
    return f"wsaudchain-{uuid.uuid4().hex[:16]}"


class WorkspaceGovernanceStore:
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
                """CREATE TABLE IF NOT EXISTS workspace_governance_state (
                    workspace_id TEXT PRIMARY KEY,
                    sensitivity TEXT NOT NULL DEFAULT 'general',
                    lifecycle_state TEXT NOT NULL DEFAULT 'active',
                    requires_approval INTEGER NOT NULL DEFAULT 0,
                    immutable INTEGER NOT NULL DEFAULT 0,
                    certified_at TEXT,
                    certified_by TEXT,
                    updated_at TEXT NOT NULL)""")
            self._conn.execute(
                """CREATE TABLE IF NOT EXISTS workspace_roles (
                    workspace_id TEXT NOT NULL,
                    operator_id TEXT NOT NULL,
                    role TEXT NOT NULL,
                    granted_by TEXT NOT NULL,
                    granted_at TEXT NOT NULL,
                    PRIMARY KEY (workspace_id, operator_id))""")
            self._conn.execute(
                "CREATE INDEX IF NOT EXISTS workspace_roles_workspace_idx "
                "ON workspace_roles (workspace_id)")
            self._conn.execute(
                """CREATE TABLE IF NOT EXISTS workspace_snapshots (
                    id TEXT PRIMARY KEY,
                    workspace_id TEXT NOT NULL,
                    version INTEGER NOT NULL,
                    snapshot_type TEXT NOT NULL,
                    actor_id TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    content_hash TEXT NOT NULL,
                    previous_hash TEXT,
                    snapshot_hash TEXT NOT NULL,
                    payload TEXT NOT NULL)""")
            self._conn.execute(
                "CREATE INDEX IF NOT EXISTS workspace_snapshots_workspace_idx "
                "ON workspace_snapshots (workspace_id, timestamp)")
            self._conn.execute(
                """CREATE TABLE IF NOT EXISTS workspace_audit_chain (
                    id TEXT PRIMARY KEY,
                    workspace_id TEXT NOT NULL,
                    actor_id TEXT NOT NULL,
                    action TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    details TEXT NOT NULL,
                    previous_hash TEXT,
                    audit_hash TEXT NOT NULL)""")
            self._conn.execute(
                "CREATE INDEX IF NOT EXISTS workspace_audit_chain_workspace_idx "
                "ON workspace_audit_chain (workspace_id, timestamp)")
            self._conn.commit()

    def close(self) -> None:
        with self._lock:
            self._conn.close()

    def ensure_governance_state(self, workspace_id: str,
                                owner_id: str) -> Dict[str, Any]:
        with self._lock:
            self._conn.execute(
                """INSERT OR IGNORE INTO workspace_governance_state (
                    workspace_id, sensitivity, lifecycle_state,
                    requires_approval, immutable, certified_at, certified_by,
                    updated_at)
                   VALUES (?, 'general', 'active', 0, 0, NULL, NULL, ?)""",
                (workspace_id, utc_now_iso()))
            self._conn.commit()
        return self.get_governance_state(workspace_id)

    def get_governance_state(self, workspace_id: str) -> Dict[str, Any]:
        with self._lock:
            row = self._conn.execute(
                "SELECT * FROM workspace_governance_state WHERE workspace_id = ?",
                (workspace_id,)).fetchone()
        if row is None:
            return {"workspace_id": workspace_id, "sensitivity": "general",
                    "lifecycle_state": "active", "requires_approval": False,
                    "immutable": False, "certified_at": None,
                    "certified_by": None, "updated_at": None}
        return self._row_to_governance_state(row)

    def update_governance_state(self, workspace_id: str,
                                updates: Dict[str, Any]) -> Dict[str, Any]:
        allowed_fields = {"sensitivity", "lifecycle_state",
                          "requires_approval", "immutable", "certified_at",
                          "certified_by"}
        sets: List[str] = []
        params: List[Any] = []
        for key, value in updates.items():
            if key not in allowed_fields:
                continue
            if key == "sensitivity" and value not in SENSITIVITY_LEVELS:
                raise ValueError("invalid sensitivity level")
            if key == "lifecycle_state" and value not in LIFECYCLE_STATES:
                raise ValueError("invalid lifecycle state")
            if key in {"requires_approval", "immutable"}:
                value = 1 if bool(value) else 0
            sets.append(f"{key} = ?")
            params.append(value)
        if not sets:
            return self.get_governance_state(workspace_id)
        sets.append("updated_at = ?")
        params.append(utc_now_iso())
        params.append(workspace_id)
        with self._lock:
            self._conn.execute(
                f"UPDATE workspace_governance_state SET {', '.join(sets)} "
                f"WHERE workspace_id = ?", params)
            self._conn.commit()
        return self.get_governance_state(workspace_id)

    def get_roles(self, workspace_id: str) -> Dict[str, str]:
        with self._lock:
            rows = self._conn.execute(
                "SELECT operator_id, role FROM workspace_roles "
                "WHERE workspace_id = ? ORDER BY operator_id ASC",
                (workspace_id,)).fetchall()
        return {row["operator_id"]: row["role"] for row in rows}

    def grant_role(self, workspace_id: str, operator_id: str, role: str,
                   granted_by: str) -> Dict[str, Any]:
        if role not in ASSIGNABLE_WORKSPACE_ROLES:
            raise ValueError("invalid workspace role")
        record = {"workspace_id": workspace_id, "operator_id": operator_id,
                  "role": role, "granted_by": granted_by,
                  "granted_at": utc_now_iso()}
        with self._lock:
            self._conn.execute(
                """INSERT INTO workspace_roles (workspace_id, operator_id,
                    role, granted_by, granted_at)
                   VALUES (?, ?, ?, ?, ?)
                   ON CONFLICT(workspace_id, operator_id)
                   DO UPDATE SET role = excluded.role,
                       granted_by = excluded.granted_by,
                       granted_at = excluded.granted_at""",
                (record["workspace_id"], record["operator_id"],
                 record["role"], record["granted_by"], record["granted_at"]))
            self._conn.commit()
        return record

    def revoke_role(self, workspace_id: str, operator_id: str) -> None:
        with self._lock:
            self._conn.execute(
                "DELETE FROM workspace_roles "
                "WHERE workspace_id = ? AND operator_id = ?",
                (workspace_id, operator_id))
            self._conn.commit()

    def latest_snapshot(self, workspace_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            row = self._conn.execute(
                "SELECT * FROM workspace_snapshots WHERE workspace_id = ? "
                "ORDER BY timestamp DESC, id DESC LIMIT 1",
                (workspace_id,)).fetchone()
        if row is None:
            return None
        return self._row_to_snapshot(row)

    def get_snapshots(self, workspace_id: str,
                      limit: int = 200) -> List[Dict[str, Any]]:
        with self._lock:
            rows = self._conn.execute(
                "SELECT * FROM workspace_snapshots WHERE workspace_id = ? "
                "ORDER BY timestamp DESC, id DESC LIMIT ?",
                (workspace_id, limit)).fetchall()
        return [self._row_to_snapshot(row) for row in rows]

    def add_snapshot(self, workspace: Dict[str, Any],
                     state: Dict[str, Any], actor_id: str,
                     snapshot_type: str) -> Dict[str, Any]:
        previous = self.latest_snapshot(workspace["id"])
        previous_hash = previous["snapshot_hash"] if previous else None
        content_hash = workspace_governance_hash(workspace, state)
        timestamp = utc_now_iso()
        snapshot_payload = {
            "workspace_id": workspace["id"],
            "version": workspace.get("version"),
            "snapshot_type": snapshot_type,
            "actor_id": actor_id,
            "timestamp": timestamp,
            "content_hash": content_hash,
            "previous_hash": previous_hash,
        }
        snapshot_hash = sha256_hex(canonical_json(snapshot_payload))
        snapshot = {
            "id": generate_snapshot_id(),
            "workspace_id": workspace["id"],
            "version": workspace.get("version"),
            "snapshot_type": snapshot_type,
            "actor_id": actor_id,
            "timestamp": timestamp,
            "content_hash": content_hash,
            "previous_hash": previous_hash,
            "snapshot_hash": snapshot_hash,
            "payload": {"workspace": workspace, "state": state},
        }
        with self._lock:
            self._conn.execute(
                """INSERT INTO workspace_snapshots (id, workspace_id, version,
                    snapshot_type, actor_id, timestamp, content_hash,
                    previous_hash, snapshot_hash, payload)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (snapshot["id"], snapshot["workspace_id"],
                 snapshot["version"], snapshot["snapshot_type"],
                 snapshot["actor_id"], snapshot["timestamp"],
                 snapshot["content_hash"], snapshot["previous_hash"],
                 snapshot["snapshot_hash"],
                 json.dumps(snapshot["payload"], sort_keys=True,
                            default=str)))
            self._conn.commit()
        return snapshot

    def add_audit_chain(self, workspace_id: str, actor_id: str, action: str,
                        details: Optional[Dict[str, Any]] = None
                        ) -> Dict[str, Any]:
        previous = self.latest_audit_chain(workspace_id)
        previous_hash = previous["audit_hash"] if previous else None
        timestamp = utc_now_iso()
        audit_payload = {
            "workspace_id": workspace_id, "actor_id": actor_id,
            "action": action, "timestamp": timestamp,
            "details": details or {}, "previous_hash": previous_hash,
        }
        audit_hash = sha256_hex(canonical_json(audit_payload))
        record = {
            "id": generate_audit_chain_id(), "workspace_id": workspace_id,
            "actor_id": actor_id, "action": action, "timestamp": timestamp,
            "details": details or {}, "previous_hash": previous_hash,
            "audit_hash": audit_hash,
        }
        with self._lock:
            self._conn.execute(
                """INSERT INTO workspace_audit_chain (id, workspace_id,
                    actor_id, action, timestamp, details, previous_hash,
                    audit_hash)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (record["id"], record["workspace_id"], record["actor_id"],
                 record["action"], record["timestamp"],
                 json.dumps(record["details"], sort_keys=True, default=str),
                 record["previous_hash"], record["audit_hash"]))
            self._conn.commit()
        return record

    def latest_audit_chain(self, workspace_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            row = self._conn.execute(
                "SELECT * FROM workspace_audit_chain WHERE workspace_id = ? "
                "ORDER BY timestamp DESC, id DESC LIMIT 1",
                (workspace_id,)).fetchone()
        if row is None:
            return None
        return self._row_to_audit_chain(row)

    def get_audit_chain(self, workspace_id: str,
                        limit: int = 200) -> List[Dict[str, Any]]:
        with self._lock:
            rows = self._conn.execute(
                "SELECT * FROM workspace_audit_chain WHERE workspace_id = ? "
                "ORDER BY timestamp DESC, id DESC LIMIT ?",
                (workspace_id, limit)).fetchall()
        return [self._row_to_audit_chain(row) for row in rows]

    def _row_to_governance_state(self, row: sqlite3.Row) -> Dict[str, Any]:
        return {
            "workspace_id": row["workspace_id"],
            "sensitivity": row["sensitivity"],
            "lifecycle_state": row["lifecycle_state"],
            "requires_approval": bool(row["requires_approval"]),
            "immutable": bool(row["immutable"]),
            "certified_at": row["certified_at"],
            "certified_by": row["certified_by"],
            "updated_at": row["updated_at"],
        }

    def _row_to_snapshot(self, row: sqlite3.Row) -> Dict[str, Any]:
        return {
            "id": row["id"], "workspace_id": row["workspace_id"],
            "version": row["version"], "snapshot_type": row["snapshot_type"],
            "actor_id": row["actor_id"], "timestamp": row["timestamp"],
            "content_hash": row["content_hash"],
            "previous_hash": row["previous_hash"],
            "snapshot_hash": row["snapshot_hash"],
            "payload": json.loads(row["payload"]),
        }

    def _row_to_audit_chain(self, row: sqlite3.Row) -> Dict[str, Any]:
        return {
            "id": row["id"], "workspace_id": row["workspace_id"],
            "actor_id": row["actor_id"], "action": row["action"],
            "timestamp": row["timestamp"],
            "details": json.loads(row["details"]),
            "previous_hash": row["previous_hash"],
            "audit_hash": row["audit_hash"],
        }
