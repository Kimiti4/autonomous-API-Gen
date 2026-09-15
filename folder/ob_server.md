Yes — proceeding with **server-side operator workspaces**.

This moves saved Observatory traces from browser-local convenience into governed, durable backend artifacts.

Server-side workspaces introduce persistent state, so they must be treated more carefully than read-only views.

They require:

```text
operator attribution
read authorization
owner-controlled mutation
visibility scoping
audit trail
export control
no secrets in workspace definitions
integration with the authenticated proxy boundary
```

This implementation remains aligned with the Constitution:

```text
Security by design.
Observability by design.
Explicit interfaces.
Loose coupling.
Production-first code.
No unnecessary complexity.
```

---

# 1. What this adds

This batch adds:

```text
backend workspace storage
backend workspace service
backend workspace API
workspace audit trail
workspace events emitted into the Observatory event stream
Next.js authenticated workspace proxy
frontend workspaces page
frontend server-workspace save panel
console workspace loading via query parameter
```

New backend endpoints:

```text
POST   /observatory/workspaces
GET    /observatory/workspaces
GET    /observatory/workspaces/{workspace_id}
PUT    /observatory/workspaces/{workspace_id}
DELETE /observatory/workspaces/{workspace_id}
GET    /observatory/workspaces/{workspace_id}/export
GET    /observatory/workspaces/{workspace_id}/audit
```

New frontend routes:

```text
/workspaces
/api/workspaces/[[...path]]
```

---

# 2. Environment configuration

Add these to your backend environment:

```bash
OBSERVATORY_WORKSPACES_ENABLED=false
OBSERVATORY_WORKSPACES_ALLOW_INSECURE_LOCAL=false
OBSERVATORY_API_TOKEN=
```

Recommended production posture:

```bash
OBSERVATORY_WORKSPACES_ENABLED=true
OBSERVATORY_WORKSPACES_ALLOW_INSECURE_LOCAL=false
OBSERVATORY_API_TOKEN=<strong-secret>
```

For the frontend proxy:

```bash
OBSERVATORY_WORKSPACES_PROXY_ENABLED=false
OBSERVATORY_BACKEND_URL=http://127.0.0.1:8000
OBSERVATORY_BACKEND_TOKEN=
OBSERVATORY_SESSION_SECRET=
```

Recommended production posture:

```bash
OBSERVATORY_WORKSPACES_PROXY_ENABLED=true
OBSERVATORY_BACKEND_URL=http://127.0.0.1:8000
OBSERVATORY_BACKEND_TOKEN=<strong-secret>
```

Do **not** expose `OBSERVATORY_BACKEND_TOKEN` as a `NEXT_PUBLIC_` variable.

---

# 3. Backend: workspace store

Create:

**`observatory/backend/workspaces_store.py`**

```python
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
                """
            )

            self._conn.execute(
                """
                CREATE INDEX IF NOT EXISTS workspaces_owner_idx
                ON workspaces (owner_id)
                """
            )

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
                """
            )

            self._conn.execute(
                """
                CREATE INDEX IF NOT EXISTS workspace_audit_workspace_idx
                ON workspace_audit (workspace_id, timestamp)
                """
            )

            self._conn.commit()

    def create_workspace(self, workspace: Dict[str, Any]) -> Dict[str, Any]:
        with self._lock:
            self._conn.execute(
                """
                INSERT INTO workspaces (
                    id,
                    name,
                    description,
                    owner_id,
                    visibility,
                    shared_with,
                    tags,
                    query,
                    created_at,
                    updated_at,
                    version
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    workspace["id"],
                    workspace["name"],
                    workspace["description"],
                    workspace["owner_id"],
                    workspace["visibility"],
                    json.dumps(workspace["shared_with"], sort_keys=True),
                    json.dumps(workspace["tags"], sort_keys=True),
                    json.dumps(workspace["query"], sort_keys=True),
                    workspace["created_at"],
                    workspace["updated_at"],
                    workspace["version"],
                ),
            )
            self._conn.commit()

        return workspace

    def get_workspace(self, workspace_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            row = self._conn.execute(
                "SELECT * FROM workspaces WHERE id = ?",
                (workspace_id,),
            ).fetchone()

        if row is None:
            return None

        return self._row_to_workspace(row)

    def list_workspaces(self) -> List[Dict[str, Any]]:
        with self._lock:
            rows = self._conn.execute(
                """
                SELECT *
                FROM workspaces
                ORDER BY updated_at DESC, id ASC
                """
            ).fetchall()

        return [self._row_to_workspace(row) for row in rows]

    def update_workspace(
        self,
        workspace_id: str,
        owner_id: str,
        updates: Dict[str, Any],
    ) -> Dict[str, Any]:
        with self._lock:
            row = self._conn.execute(
                "SELECT * FROM workspaces WHERE id = ?",
                (workspace_id,),
            ).fetchone()

            if row is None:
                raise WorkspaceNotFound(workspace_id)

            current = self._row_to_workspace(row)

            if current["owner_id"] != owner_id:
                raise WorkspacePermissionDenied(workspace_id)

            updated = dict(current)

            for key in (
                "name",
                "description",
                "visibility",
                "shared_with",
                "tags",
                "query",
            ):
                if key in updates:
                    updated[key] = updates[key]

            updated["updated_at"] = utc_now_iso()
            updated["version"] = current["version"] + 1

            self._conn.execute(
                """
                UPDATE workspaces
                SET
                    name = ?,
                    description = ?,
                    visibility = ?,
                    shared_with = ?,
                    tags = ?,
                    query = ?,
                    updated_at = ?,
                    version = ?
                WHERE id = ?
                """,
                (
                    updated["name"],
                    updated["description"],
                    updated["visibility"],
                    json.dumps(updated["shared_with"], sort_keys=True),
                    json.dumps(updated["tags"], sort_keys=True),
                    json.dumps(updated["query"], sort_keys=True),
                    updated["updated_at"],
                    updated["version"],
                    workspace_id,
                ),
            )

            self._conn.commit()

        return updated

    def delete_workspace(self, workspace_id: str, owner_id: str) -> Dict[str, Any]:
        with self._lock:
            row = self._conn.execute(
                "SELECT * FROM workspaces WHERE id = ?",
                (workspace_id,),
            ).fetchone()

            if row is None:
                raise WorkspaceNotFound(workspace_id)

            workspace = self._row_to_workspace(row)

            if workspace["owner_id"] != owner_id:
                raise WorkspacePermissionDenied(workspace_id)

            self._conn.execute(
                "DELETE FROM workspaces WHERE id = ?",
                (workspace_id,),
            )

            self._conn.commit()

        return workspace

    def add_audit(
        self,
        workspace_id: str,
        actor_id: str,
        action: str,
        details: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        audit_record = {
            "id": generate_audit_id(),
            "workspace_id": workspace_id,
            "actor_id": actor_id,
            "action": action,
            "timestamp": utc_now_iso(),
            "details": details or {},
        }

        with self._lock:
            self._conn.execute(
                """
                INSERT INTO workspace_audit (
                    id,
                    workspace_id,
                    actor_id,
                    action,
                    timestamp,
                    details
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    audit_record["id"],
                    audit_record["workspace_id"],
                    audit_record["actor_id"],
                    audit_record["action"],
                    audit_record["timestamp"],
                    json.dumps(audit_record["details"], sort_keys=True),
                ),
            )
            self._conn.commit()

        return audit_record

    def get_audit(self, workspace_id: str, limit: int = 200) -> List[Dict[str, Any]]:
        with self._lock:
            rows = self._conn.execute(
                """
                SELECT *
                FROM workspace_audit
                WHERE workspace_id = ?
                ORDER BY timestamp DESC, id DESC
                LIMIT ?
                """,
                (workspace_id, limit),
            ).fetchall()

        return [self._row_to_audit(row) for row in rows]

    def _row_to_workspace(self, row: sqlite3.Row) -> Dict[str, Any]:
        return {
            "id": row["id"],
            "name": row["name"],
            "description": row["description"],
            "owner_id": row["owner_id"],
            "visibility": row["visibility"],
            "shared_with": json.loads(row["shared_with"]),
            "tags": json.loads(row["tags"]),
            "query": json.loads(row["query"]),
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
            "version": row["version"],
        }

    def _row_to_audit(self, row: sqlite3.Row) -> Dict[str, Any]:
        return {
            "id": row["id"],
            "workspace_id": row["workspace_id"],
            "actor_id": row["actor_id"],
            "action": row["action"],
            "timestamp": row["timestamp"],
            "details": json.loads(row["details"]),
        }
```

---

# 4. Backend: workspace service

Create:

**`observatory/backend/workspaces_service.py`**

```python
from __future__ import annotations

from typing import Any, Dict, List, Optional

from .domain import EpistemicStatus, EventCategory, new_event
from .workspaces_store import (
    SqliteWorkspaceStore,
    WorkspaceNotFound,
    WorkspacePermissionDenied,
    generate_workspace_id,
    utc_now_iso,
)

ALLOWED_VISIBILITIES = {"private", "shared", "public"}


class WorkspaceRequestValidationError(Exception):
    pass


def _clean_string(
    value: Any,
    field: str,
    max_length: int = 500,
    required: bool = False,
) -> Optional[str]:
    if value is None:
        if required:
            raise WorkspaceRequestValidationError(f"{field} is required")
        return None

    cleaned = str(value).strip()

    if len(cleaned) == 0:
        if required:
            raise WorkspaceRequestValidationError(f"{field} is required")
        return ""

    if len(cleaned) > max_length:
        raise WorkspaceRequestValidationError(f"{field} exceeds maximum length")

    return cleaned


def _clean_string_list(value: Any, field: str) -> List[str]:
    if value is None:
        return []

    if not isinstance(value, list):
        raise WorkspaceRequestValidationError(f"{field} must be a list")

    cleaned: List[str] = []

    for item in value:
        item_string = str(item).strip()

        if item_string:
            cleaned.append(item_string)

    return sorted(set(cleaned))


def validate_query(query: Any) -> Dict[str, Any]:
    if not isinstance(query, dict):
        raise WorkspaceRequestValidationError("query must be an object")

    normalized: Dict[str, Any] = {}

    q = _clean_string(query.get("q"), "query.q", max_length=1000)
    if q:
        normalized["q"] = q

    normalized["categories"] = _clean_string_list(
        query.get("categories"),
        "query.categories",
    )
    normalized["severities"] = _clean_string_list(
        query.get("severities"),
        "query.severities",
    )
    normalized["epistemic_statuses"] = _clean_string_list(
        query.get("epistemic_statuses"),
        "query.epistemic_statuses",
    )

    since = _clean_string(query.get("since"), "query.since", max_length=100)
    until = _clean_string(query.get("until"), "query.until", max_length=100)

    if since:
        normalized["since"] = since

    if until:
        normalized["until"] = until

    raw_limit = query.get("limit", 200)

    try:
        limit = int(raw_limit)
    except (TypeError, ValueError) as exc:
        raise WorkspaceRequestValidationError("query.limit must be an integer") from exc

    if limit < 1 or limit > 1000:
        raise WorkspaceRequestValidationError("query.limit must be between 1 and 1000")

    normalized["limit"] = limit

    return normalized


def validate_workspace_payload(
    payload: Any,
    partial: bool = False,
) -> Dict[str, Any]:
    if not isinstance(payload, dict):
        raise WorkspaceRequestValidationError("workspace payload must be an object")

    normalized: Dict[str, Any] = {}

    if not partial or "name" in payload:
        normalized["name"] = _clean_string(
            payload.get("name"),
            "name",
            max_length=200,
            required=not partial,
        )

    if not partial or "description" in payload:
        normalized["description"] = _clean_string(
            payload.get("description"),
            "description",
            max_length=2000,
        ) or ""

    if not partial or "visibility" in payload:
        visibility = _clean_string(
            payload.get("visibility"),
            "visibility",
            max_length=20,
            required=not partial,
        )

        if visibility not in ALLOWED_VISIBILITIES:
            raise WorkspaceRequestValidationError(
                "visibility must be private, shared, or public"
            )

        normalized["visibility"] = visibility

    if not partial or "shared_with" in payload:
        normalized["shared_with"] = _clean_string_list(
            payload.get("shared_with"),
            "shared_with",
        )

    if not partial or "tags" in payload:
        normalized["tags"] = _clean_string_list(payload.get("tags"), "tags")

    if not partial or "query" in payload:
        if "query" not in payload and partial:
            pass
        else:
            normalized["query"] = validate_query(payload.get("query"))

    if not partial:
        if normalized.get("visibility") == "shared" and not normalized.get("shared_with"):
            raise WorkspaceRequestValidationError(
                "shared workspaces require at least one shared_with operator"
            )

    return normalized


def can_read_workspace(workspace: Dict[str, Any], actor_id: str) -> bool:
    if workspace["owner_id"] == actor_id:
        return True

    if workspace["visibility"] == "public":
        return True

    if workspace["visibility"] == "shared" and actor_id in workspace["shared_with"]:
        return True

    return False


class WorkspaceService:
    def __init__(
        self,
        workspace_store: SqliteWorkspaceStore,
        event_store: Any,
    ) -> None:
        self.workspace_store = workspace_store
        self.event_store = event_store

    def create_workspace(
        self,
        actor: Dict[str, str],
        payload: Dict[str, Any],
    ) -> Dict[str, Any]:
        normalized = validate_workspace_payload(payload, partial=False)

        workspace = {
            "id": generate_workspace_id(),
            "name": normalized["name"],
            "description": normalized.get("description", ""),
            "owner_id": actor["id"],
            "visibility": normalized["visibility"],
            "shared_with": normalized.get("shared_with", []),
            "tags": normalized.get("tags", []),
            "query": normalized["query"],
            "created_at": utc_now_iso(),
            "updated_at": utc_now_iso(),
            "version": 1,
        }

        created = self.workspace_store.create_workspace(workspace)

        self.workspace_store.add_audit(
            created["id"],
            actor["id"],
            "workspace_created",
            {
                "name": created["name"],
                "visibility": created["visibility"],
            },
        )

        self._emit_event("created", created, actor)

        return created

    def get_workspace(
        self,
        actor: Dict[str, str],
        workspace_id: str,
    ) -> Dict[str, Any]:
        workspace = self.workspace_store.get_workspace(workspace_id)

        if workspace is None:
            raise WorkspaceNotFound(workspace_id)

        if not can_read_workspace(workspace, actor["id"]):
            raise WorkspacePermissionDenied(workspace_id)

        return workspace

    def list_workspaces(self, actor: Dict[str, str]) -> List[Dict[str, Any]]:
        all_workspaces = self.workspace_store.list_workspaces()

        return [
            workspace
            for workspace in all_workspaces
            if can_read_workspace(workspace, actor["id"])
        ]

    def update_workspace(
        self,
        actor: Dict[str, str],
        workspace_id: str,
        payload: Dict[str, Any],
    ) -> Dict[str, Any]:
        existing = self.workspace_store.get_workspace(workspace_id)

        if existing is None:
            raise WorkspaceNotFound(workspace_id)

        if existing["owner_id"] != actor["id"]:
            raise WorkspacePermissionDenied(workspace_id)

        normalized = validate_workspace_payload(payload, partial=True)

        if normalized.get("visibility") == "shared":
            shared_with = normalized.get("shared_with", existing["shared_with"])

            if not shared_with:
                raise WorkspaceRequestValidationError(
                    "shared workspaces require at least one shared_with operator"
                )

            normalized["shared_with"] = shared_with

        updated = self.workspace_store.update_workspace(
            workspace_id,
            actor["id"],
            normalized,
        )

        self.workspace_store.add_audit(
            workspace_id,
            actor["id"],
            "workspace_updated",
            {
                "updated_fields": sorted(normalized.keys()),
            },
        )

        self._emit_event("updated", updated, actor)

        return updated

    def delete_workspace(
        self,
        actor: Dict[str, str],
        workspace_id: str,
    ) -> Dict[str, Any]:
        deleted = self.workspace_store.delete_workspace(workspace_id, actor["id"])

        self.workspace_store.add_audit(
            workspace_id,
            actor["id"],
            "workspace_deleted",
            {
                "name": deleted["name"],
            },
        )

        self._emit_event("deleted", deleted, actor)

        return deleted

    def export_workspace(
        self,
        actor: Dict[str, str],
        workspace_id: str,
    ) -> Dict[str, Any]:
        workspace = self.get_workspace(actor, workspace_id)

        self.workspace_store.add_audit(
            workspace_id,
            actor["id"],
            "workspace_exported",
            {},
        )

        self._emit_event("exported", workspace, actor)

        return {
            "bundle_version": "observatory-workspace-export-v1",
            "workspace": workspace,
            "exported_by": actor["id"],
            "exported_at": utc_now_iso(),
        }

    def get_audit(
        self,
        actor: Dict[str, str],
        workspace_id: str,
        limit: int = 200,
    ) -> List[Dict[str, Any]]:
        self.get_workspace(actor, workspace_id)

        return self.workspace_store.get_audit(workspace_id, limit=limit)

    def _emit_event(
        self,
        action: str,
        workspace: Dict[str, Any],
        actor: Dict[str, str],
    ) -> None:
        event = new_event(
            category=EventCategory.KNOWLEDGE,
            type=f"workspace_{action}",
            subject_id=workspace["id"],
            source="observatory.workspaces",
            payload={
                "workspace_id": workspace["id"],
                "workspace_name": workspace["name"],
                "owner_id": workspace["owner_id"],
                "visibility": workspace["visibility"],
                "action": action,
                "actor_id": actor["id"],
                "summary": f"Workspace {workspace['name']} {action}",
            },
            epistemic_status=EpistemicStatus.OBSERVED,
            severity="info",
        )

        self.event_store.append(event)
```

---

# 5. Backend: workspace API routes

Create:

**`observatory/backend/workspaces_routes.py`**

```python
from __future__ import annotations

import asyncio
import os
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from .workspaces_service import (
    WorkspaceRequestValidationError,
    WorkspaceService,
)
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


def workspaces_enabled() -> bool:
    return os.getenv("OBSERVATORY_WORKSPACES_ENABLED", "false").strip().lower() == "true"


def allow_insecure_local() -> bool:
    return (
        os.getenv("OBSERVATORY_WORKSPACES_ALLOW_INSECURE_LOCAL", "false")
        .strip()
        .lower()
        == "true"
    )


def require_workspace_actor(request: Request) -> dict[str, str]:
    if not workspaces_enabled():
        raise HTTPException(status_code=403, detail="workspaces_disabled")

    actor_id = request.headers.get("x-operator-id") or request.headers.get("x-actor-id")
    role = (
        request.headers.get("x-operator-role")
        or request.headers.get("x-actor-role")
        or "observer"
    )
    clearance = (
        request.headers.get("x-operator-clearance")
        or request.headers.get("x-actor-clearance")
        or role
    )

    if not actor_id:
        raise HTTPException(status_code=401, detail="operator_id_required")

    token = request.headers.get("x-observatory-token")
    expected_token = os.getenv("OBSERVATORY_API_TOKEN")

    if expected_token:
        if token != expected_token:
            raise HTTPException(status_code=401, detail="invalid_token")
    elif not allow_insecure_local():
        raise HTTPException(
            status_code=403,
            detail="workspace_auth_not_configured",
        )

    return {
        "id": actor_id,
        "role": role,
        "clearance": clearance,
    }


def get_workspace_service(request: Request) -> WorkspaceService:
    workspace_store: SqliteWorkspaceStore = request.app.state.workspace_store
    event_store = request.app.state.gateway.store

    return WorkspaceService(workspace_store, event_store)


@router.post("")
async def create_workspace(
    payload: WorkspaceCreateRequest,
    actor: dict[str, str] = Depends(require_workspace_actor),
    service: WorkspaceService = Depends(get_workspace_service),
):
    try:
        return await asyncio.to_thread(
            service.create_workspace,
            actor,
            payload.model_dump(),
        )
    except WorkspaceRequestValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("")
async def list_workspaces(
    actor: dict[str, str] = Depends(require_workspace_actor),
    service: WorkspaceService = Depends(get_workspace_service),
):
    return await asyncio.to_thread(service.list_workspaces, actor)


@router.get("/{workspace_id}")
async def get_workspace(
    workspace_id: str,
    actor: dict[str, str] = Depends(require_workspace_actor),
    service: WorkspaceService = Depends(get_workspace_service),
):
    try:
        return await asyncio.to_thread(
            service.get_workspace,
            actor,
            workspace_id,
        )
    except WorkspaceNotFound as exc:
        raise HTTPException(status_code=404, detail="workspace_not_found") from exc
    except WorkspacePermissionDenied as exc:
        raise HTTPException(status_code=403, detail="workspace_access_denied") from exc


@router.put("/{workspace_id}")
async def update_workspace(
    workspace_id: str,
    payload: WorkspaceUpdateRequest,
    actor: dict[str, str] = Depends(require_workspace_actor),
    service: WorkspaceService = Depends(get_workspace_service),
):
    try:
        return await asyncio.to_thread(
            service.update_workspace,
            actor,
            workspace_id,
            payload.model_dump(exclude_unset=True),
        )
    except WorkspaceNotFound as exc:
        raise HTTPException(status_code=404, detail="workspace_not_found") from exc
    except WorkspacePermissionDenied as exc:
        raise HTTPException(status_code=403, detail="workspace_access_denied") from exc
    except WorkspaceRequestValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.delete("/{workspace_id}")
async def delete_workspace(
    workspace_id: str,
    actor: dict[str, str] = Depends(require_workspace_actor),
    service: WorkspaceService = Depends(get_workspace_service),
):
    try:
        deleted = await asyncio.to_thread(
            service.delete_workspace,
            actor,
            workspace_id,
        )

        return {
            "status": "deleted",
            "workspace_id": deleted["id"],
        }
    except WorkspaceNotFound as exc:
        raise HTTPException(status_code=404, detail="workspace_not_found") from exc
    except WorkspacePermissionDenied as exc:
        raise HTTPException(status_code=403, detail="workspace_access_denied") from exc


@router.get("/{workspace_id}/export")
async def export_workspace(
    workspace_id: str,
    actor: dict[str, str] = Depends(require_workspace_actor),
    service: WorkspaceService = Depends(get_workspace_service),
):
    try:
        return await asyncio.to_thread(
            service.export_workspace,
            actor,
            workspace_id,
        )
    except WorkspaceNotFound as exc:
        raise HTTPException(status_code=404, detail="workspace_not_found") from exc
    except WorkspacePermissionDenied as exc:
        raise HTTPException(status_code=403, detail="workspace_access_denied") from exc


@router.get("/{workspace_id}/audit")
async def get_workspace_audit(
    workspace_id: str,
    limit: int = 200,
    actor: dict[str, str] = Depends(require_workspace_actor),
    service: WorkspaceService = Depends(get_workspace_service),
):
    try:
        return await asyncio.to_thread(
            service.get_audit,
            actor,
            workspace_id,
            limit,
        )
    except WorkspaceNotFound as exc:
        raise HTTPException(status_code=404, detail="workspace_not_found") from exc
    except WorkspacePermissionDenied as exc:
        raise HTTPException(status_code=403, detail="workspace_access_denied") from exc
```

---

# 6. Backend: wire workspaces into the app

Update:

**`observatory/backend/main.py`**

Add imports:

```python
from .workspaces_routes import router as workspaces_router
from .workspaces_store import SqliteWorkspaceStore
```

Inside `create_app`, after the Observatory gateway is created:

```python
    workspace_store = SqliteWorkspaceStore(settings.db_path)
    workspace_store.init()

    app.state.workspace_store = workspace_store
    app.include_router(workspaces_router)
```

---

# 7. Frontend: authenticated workspace proxy

Create:

**`observatory/frontend/app/api/workspaces/[[...path]]/route.ts`**

```typescript
import { NextRequest, NextResponse } from "next/server";

import { getSession } from "@/lib/auth";

export const runtime = "nodejs";

type RouteContext = {
  params: {
    path?: string[];
  };
};

function proxyEnabled(): boolean {
  return process.env.OBSERVATORY_WORKSPACES_PROXY_ENABLED === "true";
}

async function proxyRequest(request: NextRequest, context: RouteContext) {
  if (!proxyEnabled()) {
    return NextResponse.json(
      { error: "workspace_proxy_disabled" },
      { status: 403 }
    );
  }

  const session = getSession();

  if (!session) {
    return NextResponse.json({ error: "unauthorized" }, { status: 401 });
  }

  const backendUrl =
    process.env.OBSERVATORY_BACKEND_URL ||
    process.env.NEXT_PUBLIC_OBSERVATORY_API_URL ||
    "http://127.0.0.1:8000";

  const subPath = context.params.path?.join("/") ?? "";
  const search = request.nextUrl.search || "";

  const target = `${backendUrl}/observatory/workspaces${
    subPath ? `/${subPath}` : ""
  }${search}`;

  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    "X-Operator-Id": session.sub,
    "X-Operator-Role": session.role,
    "X-Operator-Clearance": session.clearance
  };

  const backendToken = process.env.OBSERVATORY_BACKEND_TOKEN;

  if (backendToken) {
    headers["X-Observatory-Token"] = backendToken;
  }

  const init: RequestInit = {
    method: request.method,
    headers
  };

  if (request.method !== "GET" && request.method !== "HEAD") {
    init.body = await request.text();
  }

  let upstream: Response;

  try {
    upstream = await fetch(target, init);
  } catch {
    return NextResponse.json(
      { error: "workspace_backend_unavailable" },
      { status: 502 }
    );
  }

  const body = await upstream.text();

  return new NextResponse(body, {
    status: upstream.status,
    headers: {
      "Content-Type":
        upstream.headers.get("content-type") || "application/json"
    }
  });
}

export async function GET(request: NextRequest, context: RouteContext) {
  return proxyRequest(request, context);
}

export async function POST(request: NextRequest, context: RouteContext) {
  return proxyRequest(request, context);
}

export async function PUT(request: NextRequest, context: RouteContext) {
  return proxyRequest(request, context);
}

export async function DELETE(request: NextRequest, context: RouteContext) {
  return proxyRequest(request, context);
}
```

---

# 8. Frontend: workspace API client

Create:

**`observatory/frontend/lib/workspaces.ts`**

```typescript
export interface WorkspaceQuery {
  q?: string;
  categories?: string[];
  severities?: string[];
  epistemic_statuses?: string[];
  since?: string;
  until?: string;
  limit?: number;
}

export interface Workspace {
  id: string;
  name: string;
  description: string;
  owner_id: string;
  visibility: "private" | "shared" | "public";
  shared_with: string[];
  tags: string[];
  query: WorkspaceQuery;
  created_at: string;
  updated_at: string;
  version: number;
}

export interface WorkspaceAuditRecord {
  id: string;
  workspace_id: string;
  actor_id: string;
  action: string;
  timestamp: string;
  details: Record<string, unknown>;
}

async function workspaceRequest<T>(
  path: string,
  init?: RequestInit
): Promise<T> {
  const response = await fetch(`/api/workspaces${path}`, {
    cache: "no-store",
    ...init
  });

  if (!response.ok) {
    let detail: unknown = response.statusText;

    try {
      detail = await response.json();
    } catch {
      // Ignore non-JSON error bodies.
    }

    throw new Error(
      typeof detail === "string" ? detail : JSON.stringify(detail)
    );
  }

  if (response.status === 204) {
    return undefined as T;
  }

  return (await response.json()) as T;
}

export const workspacesApi = {
  list(): Promise<Workspace[]> {
    return workspaceRequest<Workspace[]>("");
  },

  get(workspaceId: string): Promise<Workspace> {
    return workspaceRequest<Workspace>(`/${encodeURIComponent(workspaceId)}`);
  },

  create(payload: {
    name: string;
    description?: string;
    query: WorkspaceQuery;
    visibility?: "private" | "shared" | "public";
    shared_with?: string[];
    tags?: string[];
  }): Promise<Workspace> {
    return workspaceRequest<Workspace>("", {
      method: "POST",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify(payload)
    });
  },

  update(
    workspaceId: string,
    payload: {
      name?: string;
      description?: string;
      query?: WorkspaceQuery;
      visibility?: "private" | "shared" | "public";
      shared_with?: string[];
      tags?: string[];
    }
  ): Promise<Workspace> {
    return workspaceRequest<Workspace>(`/${encodeURIComponent(workspaceId)}`, {
      method: "PUT",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify(payload)
    });
  },

  remove(workspaceId: string): Promise<{ status: string; workspace_id: string }> {
    return workspaceRequest<{ status: string; workspace_id: string }>(
      `/${encodeURIComponent(workspaceId)}`,
      {
        method: "DELETE"
      }
    );
  },

  audit(workspaceId: string): Promise<WorkspaceAuditRecord[]> {
    return workspaceRequest<WorkspaceAuditRecord[]>(
      `/${encodeURIComponent(workspaceId)}/audit`
    );
  },

  exportUrl(workspaceId: string): string {
    return `/api/workspaces/${encodeURIComponent(workspaceId)}/export`;
  }
};
```

---

# 9. Frontend: server workspace save panel

Create:

**`observatory/frontend/components/ServerWorkspacePanel.tsx`**

```typescript
"use client";

import { useState } from "react";

import { workspacesApi, type WorkspaceQuery } from "@/lib/workspaces";

export function ServerWorkspacePanel({
  currentQuery
}: {
  currentQuery: WorkspaceQuery;
}) {
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [visibility, setVisibility] = useState<"private" | "shared" | "public">(
    "private"
  );
  const [sharedWith, setSharedWith] = useState("");
  const [message, setMessage] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function save() {
    setBusy(true);
    setMessage(null);

    try {
      const workspace = await workspacesApi.create({
        name,
        description,
        query: currentQuery,
        visibility,
        shared_with: sharedWith
          .split(",")
          .map(item => item.trim())
          .filter(Boolean)
      });

      setMessage(`Saved workspace ${workspace.id}`);
      setName("");
      setDescription("");
      setSharedWith("");
    } catch (cause) {
      setMessage(cause instanceof Error ? cause.message : "Save failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="grid">
      <div className="notice">
        Server workspaces are persistent operator artifacts. Do not store
        secrets in workspace names, descriptions, tags, or search queries.
      </div>

      <label className="grid">
        <span className="muted">Workspace name</span>
        <input
          value={name}
          onChange={event => setName(event.target.value)}
          placeholder="Priority investigation trace"
        />
      </label>

      <label className="grid">
        <span className="muted">Description</span>
        <input
          value={description}
          onChange={event => setDescription(event.target.value)}
          placeholder="Trace for VS1 priority evidence review"
        />
      </label>

      <label className="grid">
        <span className="muted">Visibility</span>
        <select
          value={visibility}
          onChange={event =>
            setVisibility(event.target.value as "private" | "shared" | "public")
          }
        >
          <option value="private">private</option>
          <option value="shared">shared</option>
          <option value="public">public</option>
        </select>
      </label>

      {visibility === "shared" ? (
        <label className="grid">
          <span className="muted">Shared with, comma-separated operator IDs</span>
          <input
            value={sharedWith}
            onChange={event => setSharedWith(event.target.value)}
            placeholder="operator-01, operator-02"
          />
        </label>
      ) : null}

      <button onClick={save} disabled={busy || name.trim().length === 0}>
        {busy ? "Saving…" : "Save server workspace"}
      </button>

      {message ? <div className="notice">{message}</div> : null}
    </div>
  );
}
```

Export it from:

**`observatory/frontend/components/index.ts`**

```typescript
export { ServerWorkspacePanel } from "./ServerWorkspacePanel";
```

---

# 10. Frontend: workspaces management page

Create:

**`observatory/frontend/app/workspaces/page.tsx`**

```typescript
"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

import { Section, StatusPill } from "@/components";
import { workspacesApi, type Workspace } from "@/lib/workspaces";

export default function WorkspacesPage() {
  const [items, setItems] = useState<Workspace[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const refresh = useCallback(async () => {
    try {
      const nextItems = await workspacesApi.list();
      setItems(nextItems);
      setError(null);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Unknown error");
    }
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  async function remove(workspaceId: string) {
    if (!window.confirm("Delete this workspace?")) {
      return;
    }

    setBusy(true);
    setError(null);

    try {
      await workspacesApi.remove(workspaceId);
      await refresh();
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Delete failed");
    } finally {
      setBusy(false);
    }
  }

  if (error && !items) {
    return <div className="error">Workspaces unavailable: {error}</div>;
  }

  if (!items) {
    return <div className="muted">Loading workspaces…</div>;
  }

  return (
    <div className="grid">
      {error ? <div className="error">{error}</div> : null}

      <Section title="Server Workspaces">
        {items.length === 0 ? (
          <div className="empty">
            No server workspaces visible. Save a workspace from the Console.
          </div>
        ) : (
          <ul className="timeline">
            {items.map(workspace => (
              <li key={workspace.id} className="timeline-item">
                <div className="timeline-top">
                  <span>{workspace.name}</span>
                  <StatusPill status={workspace.visibility} />
                </div>

                <div className="timeline-summary">{workspace.description}</div>

                <div className="timeline-meta">
                  <span>owner {workspace.owner_id}</span>
                  <span>version {workspace.version}</span>
                  <span>
                    updated {new Date(workspace.updated_at).toLocaleString()}
                  </span>
                  <span>tags {workspace.tags.join(", ") || "none"}</span>
                  <span>
                    shared with {workspace.shared_with.join(", ") || "none"}
                  </span>
                </div>

                <div style={{ height: 8 }} />

                <div className="grid grid-3">
                  <Link href={`/console?workspace=${workspace.id}`}>
                    Apply in Console
                  </Link>

                  <a
                    href={workspacesApi.exportUrl(workspace.id)}
                    target="_blank"
                    rel="noreferrer"
                  >
                    Export
                  </a>

                  <button
                    onClick={() => remove(workspace.id)}
                    disabled={busy}
                    type="button"
                  >
                    Delete
                  </button>
                </div>
              </li>
            ))}
          </ul>
        )}
      </Section>
    </div>
  );
}
```

---

# 11. Integrate workspaces into the Console

In:

**`observatory/frontend/app/console/page.tsx`**

Add imports:

```typescript
import { ServerWorkspacePanel } from "@/components";
import { workspacesApi } from "@/lib/workspaces";
```

Inside `ConsolePage`, add this effect after the existing saved-traces effect:

```typescript
  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const workspaceId = params.get("workspace");

    if (!workspaceId) {
      return;
    }

    workspacesApi
      .get(workspaceId)
      .then(workspace => {
        setQ(workspace.query.q ?? "");
        setCategories((workspace.query.categories ?? []).join(", "));
        setSeverities((workspace.query.severities ?? []).join(", "));
        setEpistemicStatuses(
          (workspace.query.epistemic_statuses ?? []).join(", ")
        );
        setSince(workspace.query.since ?? "");
        setUntil(workspace.query.until ?? "");
        setLimit(workspace.query.limit ?? 200);
      })
      .catch(() => {
        setError("Unable to load workspace");
      });
  }, []);
```

Then render the server workspace panel after the local Saved Traces section:

```tsx
      <Section title="Server Workspaces">
        <ServerWorkspacePanel currentQuery={currentParams} />
      </Section>
```

---

# 12. Add Workspaces to navigation

Update the navigation block in:

**`observatory/frontend/app/layout.tsx`**

```tsx
          <nav className="app-nav">
            <a href="/">Overview</a>
            <a href="/console">Console</a>
            <a href="/runtime">Runtime</a>
            <a href="/requirements">Requirements</a>
            <a href="/knowledge">Knowledge</a>
            <a href="/experiments">Experiments</a>
            <a href="/fitness">Fitness</a>
            <a href="/genomes">Genomes</a>
            <a href="/decisions">Decisions</a>
            <a href="/provenance">Audit</a>
            <a href="/workspaces">Workspaces</a>
            <a href="/governance">Governance</a>
          </nav>
```

---

# 13. Workspace security model

This implementation enforces:

```text
workspaces disabled unless explicitly enabled
operator identity required
mutation only by owner
read access governed by visibility and shared_with
shared workspaces require explicit operator IDs
audit trail for create/update/delete/export
workspace changes emitted into the Observatory event stream
no browser-side backend token
proxy boundary attaches operator identity
```

This is still not a full enterprise RBAC system.

For production, integrate this with:

```text
OIDC/OAuth2 operator authentication
role-based workspace administration
workspace quotas
workspace retention policies
immutable audit export
secret scanning on workspace payloads
```

---

# 14. Verification checklist

Before treating server workspaces as production-ready, verify:

```text
workspaces disabled by default
missing operator ID returns 401
invalid backend token returns 401
unauthenticated proxy request returns 401
create workspace persists workspace
create workspace writes audit record
create workspace emits workspace_created event
private workspace is invisible to other operators
shared workspace is visible to shared operators
public workspace is visible to authenticated operators
non-owner cannot update workspace
non-owner cannot delete workspace
update increments version
update writes audit record
delete removes workspace
delete writes audit record
export writes audit record
audit endpoint respects read access
workspace export includes query and metadata
console can load workspace from ?workspace=
console can save current query as server workspace
workspaces page can apply workspace in console
workspaces page can delete owned workspace
no secrets are stored in workspace payloads
```

---

# 15. Next recommended step

The next step should be **workspace governance hardening**:

```text
OIDC-backed operator identity
workspace roles
workspace approval flows
immutable workspace snapshots
workspace diffing
workspace certification
workspace retention and export bundles
```

That would turn operator workspaces from a persistent convenience into a fully governed knowledge artifact within the Observatory.


Yes — proceeding with **workspace governance hardening**.

Server-side operator workspaces introduce persistent human-facing state. That means they must be hardened as governed artifacts, not treated as simple saved searches.

This hardening layer adds:

```text
operator identity context
role-based access control
workspace lifecycle state
sensitivity classification
immutable snapshots
tamper-evident audit chain
secret scanning
approval fail-closed behavior
governed role grants
export control
```

It preserves the Constitution:

```text
Security by design.
Observability by design.
Explicit interfaces.
Plugin-first identity and policy extension.
Least privilege.
No unnecessary complexity.
Production-first behavior.
```

---

# 1. Governance model

The hardened model treats every workspace as a governed artifact:

```text
Workspace
  ├─ owner
  ├─ visibility
  ├─ shared_with
  ├─ explicit workspace roles
  ├─ sensitivity classification
  ├─ lifecycle state
  ├─ approval requirements
  ├─ immutable snapshots
  ├─ audit chain
  └─ export governance
```

## Actions

The governed actions are:

```text
read
update
delete
share
export
audit
grant_role
revoke_role
lock
unlock
archive
restore
certify
```

## Roles

Workspace-level roles:

```text
viewer
auditor
contributor
admin
owner
```

Global roles, supplied by the identity layer:

```text
global_workspace_admin
global_auditor
workspace_creator
workspace_denied
```

## Permission intent

```text
viewer       → read
auditor      → read, audit, export
contributor  → read, update, export
admin        → read, update, share, audit, export, grant_role, revoke_role,
               lock, unlock, archive
owner        → all workspace actions
```

Global admin does **not** automatically become owner.

Global admin receives administrative control, but deletion and certification remain owner-governed unless explicitly extended later.

---

# 2. Backend: governance policy engine

Create:

**`observatory/backend/workspace_governance.py`**

```python
from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Set, Tuple


class WorkspaceGovernanceError(Exception):
    pass


class WorkspaceActionDenied(WorkspaceGovernanceError):
    pass


class WorkspaceSecretDetected(WorkspaceGovernanceError):
    pass


KNOWN_ACTIONS = {
    "create",
    "read",
    "update",
    "delete",
    "share",
    "export",
    "audit",
    "grant_role",
    "revoke_role",
    "lock",
    "unlock",
    "archive",
    "restore",
    "certify",
}

ASSIGNABLE_WORKSPACE_ROLES = {
    "viewer",
    "auditor",
    "contributor",
    "admin",
}

ROLE_PERMISSIONS: Dict[str, Set[str]] = {
    "viewer": {
        "read",
    },
    "auditor": {
        "read",
        "audit",
        "export",
    },
    "contributor": {
        "read",
        "update",
        "export",
    },
    "admin": {
        "read",
        "update",
        "share",
        "audit",
        "export",
        "grant_role",
        "revoke_role",
        "lock",
        "unlock",
        "archive",
    },
    "owner": {
        "read",
        "update",
        "delete",
        "share",
        "audit",
        "export",
        "grant_role",
        "revoke_role",
        "lock",
        "unlock",
        "archive",
        "restore",
        "certify",
    },
}

SENSITIVITY_LEVELS = {
    "general",
    "restricted",
    "confidential",
}

LIFECYCLE_STATES = {
    "active",
    "locked",
    "archived",
}

SECRET_PATTERNS = [
    ("aws_access_key_id", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("private_key", re.compile(r"-----BEGIN[A-Z ]*PRIVATE KEY-----")),
    (
        "generic_password",
        re.compile(
            r"(?i)\b(password|passwd|pwd)\b\s*[:=]\s*['\"][^'\"]{8,}['\"]"
        ),
    ),
    (
        "generic_secret",
        re.compile(
            r"(?i)\b(secret|token|api_key|apikey|access_token|refresh_token)\b"
            r"\s*[:=]\s*['\"][^'\"]{16,}['\"]"
        ),
    ),
    ("bearer_token", re.compile(r"\bBearer\s+[A-Za-z0-9\-._~+/]+=*\b")),
    (
        "database_url_with_credentials",
        re.compile(
            r"(?i)\b(postgresql|postgres|mongodb|redis|mysql)\+?://"
            r"[^:\s]+:[^@\s]+@"
        ),
    ),
]


def canonical_json(value: Any) -> str:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    )


def sha256_hex(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def workspace_governance_hash(
    workspace: Dict[str, Any],
    state: Dict[str, Any],
) -> str:
    content = {
        "workspace_id": workspace["id"],
        "name": workspace["name"],
        "description": workspace["description"],
        "owner_id": workspace["owner_id"],
        "visibility": workspace["visibility"],
        "shared_with": sorted(workspace.get("shared_with", [])),
        "tags": sorted(workspace.get("tags", [])),
        "query": workspace.get("query", {}),
        "version": workspace.get("version"),
        "sensitivity": state.get("sensitivity", "general"),
        "lifecycle_state": state.get("lifecycle_state", "active"),
        "requires_approval": bool(state.get("requires_approval", False)),
        "immutable": bool(state.get("immutable", False)),
    }

    return sha256_hex(canonical_json(content))


def scan_workspace_payload(payload: Dict[str, Any]) -> None:
    serialized = canonical_json(payload)

    for pattern_name, pattern in SECRET_PATTERNS:
        if pattern.search(serialized):
            raise WorkspaceSecretDetected(
                f"secret-shaped material detected: {pattern_name}"
            )


@dataclass(frozen=True)
class OperatorIdentity:
    operator_id: str
    roles: Tuple[str, ...]
    clearance: str
    auth_method: str

    @classmethod
    def from_actor(cls, actor: Dict[str, Any]) -> "OperatorIdentity":
        raw_roles = actor.get("roles") or []

        if not isinstance(raw_roles, list):
            raw_roles = [raw_roles]

        roles = tuple(sorted({str(role) for role in raw_roles if str(role).strip()}))

        if not roles:
            roles = (str(actor.get("role", "observer")),)

        return cls(
            operator_id=str(actor.get("id", "anonymous")),
            roles=roles,
            clearance=str(actor.get("clearance", actor.get("role", "observer"))),
            auth_method=str(actor.get("auth_method", "unknown")),
        )

    @property
    def global_roles(self) -> Set[str]:
        return set(self.roles)


@dataclass(frozen=True)
class GovernanceDecision:
    allowed: bool
    reason: str


class WorkspaceGovernor:
    def authorize_create(self, identity: OperatorIdentity) -> GovernanceDecision:
        if not identity.operator_id or identity.operator_id == "anonymous":
            return GovernanceDecision(False, "operator_identity_required")

        if "workspace_denied" in identity.global_roles:
            return GovernanceDecision(False, "operator_denied")

        if (
            identity.clearance in {"operator", "architect", "admin"}
            or "workspace_creator" in identity.global_roles
            or "global_workspace_admin" in identity.global_roles
        ):
            return GovernanceDecision(True, "create_allowed")

        return GovernanceDecision(False, "create_not_authorized")

    def effective_role(
        self,
        identity: OperatorIdentity,
        workspace: Dict[str, Any],
        workspace_roles: Dict[str, str],
    ) -> Optional[str]:
        if workspace["owner_id"] == identity.operator_id:
            return "owner"

        if "global_workspace_admin" in identity.global_roles:
            return "admin"

        explicit_role = workspace_roles.get(identity.operator_id)

        if explicit_role:
            return explicit_role

        if "global_auditor" in identity.global_roles:
            return "auditor"

        if workspace["visibility"] == "public":
            return "viewer"

        if (
            workspace["visibility"] == "shared"
            and identity.operator_id in workspace.get("shared_with", [])
        ):
            return "viewer"

        return None

    def authorize_action(
        self,
        identity: OperatorIdentity,
        workspace: Dict[str, Any],
        state: Dict[str, Any],
        action: str,
        workspace_roles: Dict[str, str],
    ) -> GovernanceDecision:
        if action not in KNOWN_ACTIONS:
            return GovernanceDecision(False, "unknown_action")

        if "workspace_denied" in identity.global_roles:
            return GovernanceDecision(False, "operator_denied")

        role = self.effective_role(identity, workspace, workspace_roles)

        if role is None:
            return GovernanceDecision(False, "no_workspace_access")

        lifecycle_state = state.get("lifecycle_state", "active")
        sensitivity = state.get("sensitivity", "general")
        requires_approval = bool(state.get("requires_approval", False))
        immutable = bool(state.get("immutable", False))

        if lifecycle_state not in LIFECYCLE_STATES:
            return GovernanceDecision(False, "invalid_lifecycle_state")

        if lifecycle_state in {"locked", "archived"} and action not in {
            "read",
            "audit",
        }:
            return GovernanceDecision(
                False,
                f"lifecycle_{lifecycle_state}_blocks_action",
            )

        if immutable and action in {
            "update",
            "delete",
            "share",
            "grant_role",
            "revoke_role",
            "lock",
            "unlock",
            "archive",
            "restore",
            "certify",
        }:
            return GovernanceDecision(False, "workspace_immutable")

        if requires_approval and action in {
            "update",
            "delete",
            "share",
            "grant_role",
            "revoke_role",
            "export",
            "lock",
            "unlock",
            "archive",
            "restore",
            "certify",
        }:
            return GovernanceDecision(False, "approval_required")

        if (
            sensitivity in {"restricted", "confidential"}
            and action == "export"
            and role not in {"owner", "admin", "auditor"}
        ):
            return GovernanceDecision(False, "sensitivity_blocks_export")

        permissions = ROLE_PERMISSIONS.get(role, set())

        if action not in permissions:
            return GovernanceDecision(False, "role_lacks_permission")

        return GovernanceDecision(True, "allowed")
```

---

# 3. Backend: governance store

Create:

**`observatory/backend/workspace_governance_store.py`**

```python
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
                """
                CREATE TABLE IF NOT EXISTS workspace_governance_state (
                    workspace_id TEXT PRIMARY KEY,
                    sensitivity TEXT NOT NULL DEFAULT 'general',
                    lifecycle_state TEXT NOT NULL DEFAULT 'active',
                    requires_approval INTEGER NOT NULL DEFAULT 0,
                    immutable INTEGER NOT NULL DEFAULT 0,
                    certified_at TEXT,
                    certified_by TEXT,
                    updated_at TEXT NOT NULL
                )
                """
            )

            self._conn.execute(
                """
                CREATE TABLE IF NOT EXISTS workspace_roles (
                    workspace_id TEXT NOT NULL,
                    operator_id TEXT NOT NULL,
                    role TEXT NOT NULL,
                    granted_by TEXT NOT NULL,
                    granted_at TEXT NOT NULL,
                    PRIMARY KEY (workspace_id, operator_id)
                )
                """
            )

            self._conn.execute(
                """
                CREATE INDEX IF NOT EXISTS workspace_roles_workspace_idx
                ON workspace_roles (workspace_id)
                """
            )

            self._conn.execute(
                """
                CREATE TABLE IF NOT EXISTS workspace_snapshots (
                    id TEXT PRIMARY KEY,
                    workspace_id TEXT NOT NULL,
                    version INTEGER NOT NULL,
                    snapshot_type TEXT NOT NULL,
                    actor_id TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    content_hash TEXT NOT NULL,
                    previous_hash TEXT,
                    snapshot_hash TEXT NOT NULL,
                    payload TEXT NOT NULL
                )
                """
            )

            self._conn.execute(
                """
                CREATE INDEX IF NOT EXISTS workspace_snapshots_workspace_idx
                ON workspace_snapshots (workspace_id, timestamp)
                """
            )

            self._conn.execute(
                """
                CREATE TABLE IF NOT EXISTS workspace_audit_chain (
                    id TEXT PRIMARY KEY,
                    workspace_id TEXT NOT NULL,
                    actor_id TEXT NOT NULL,
                    action TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    details TEXT NOT NULL,
                    previous_hash TEXT,
                    audit_hash TEXT NOT NULL
                )
                """
            )

            self._conn.execute(
                """
                CREATE INDEX IF NOT EXISTS workspace_audit_chain_workspace_idx
                ON workspace_audit_chain (workspace_id, timestamp)
                """
            )

            self._conn.commit()

    def ensure_governance_state(
        self,
        workspace_id: str,
        owner_id: str,
    ) -> Dict[str, Any]:
        with self._lock:
            self._conn.execute(
                """
                INSERT OR IGNORE INTO workspace_governance_state (
                    workspace_id,
                    sensitivity,
                    lifecycle_state,
                    requires_approval,
                    immutable,
                    certified_at,
                    certified_by,
                    updated_at
                ) VALUES (?, 'general', 'active', 0, 0, NULL, NULL, ?)
                """,
                (workspace_id, utc_now_iso()),
            )
            self._conn.commit()

        return self.get_governance_state(workspace_id)

    def get_governance_state(self, workspace_id: str) -> Dict[str, Any]:
        with self._lock:
            row = self._conn.execute(
                """
                SELECT *
                FROM workspace_governance_state
                WHERE workspace_id = ?
                """,
                (workspace_id,),
            ).fetchone()

        if row is None:
            return {
                "workspace_id": workspace_id,
                "sensitivity": "general",
                "lifecycle_state": "active",
                "requires_approval": False,
                "immutable": False,
                "certified_at": None,
                "certified_by": None,
                "updated_at": None,
            }

        return self._row_to_governance_state(row)

    def update_governance_state(
        self,
        workspace_id: str,
        updates: Dict[str, Any],
    ) -> Dict[str, Any]:
        allowed_fields = {
            "sensitivity",
            "lifecycle_state",
            "requires_approval",
            "immutable",
            "certified_at",
            "certified_by",
        }

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
                f"""
                UPDATE workspace_governance_state
                SET {", ".join(sets)}
                WHERE workspace_id = ?
                """,
                params,
            )
            self._conn.commit()

        return self.get_governance_state(workspace_id)

    def get_roles(self, workspace_id: str) -> Dict[str, str]:
        with self._lock:
            rows = self._conn.execute(
                """
                SELECT operator_id, role
                FROM workspace_roles
                WHERE workspace_id = ?
                ORDER BY operator_id ASC
                """,
                (workspace_id,),
            ).fetchall()

        return {row["operator_id"]: row["role"] for row in rows}

    def grant_role(
        self,
        workspace_id: str,
        operator_id: str,
        role: str,
        granted_by: str,
    ) -> Dict[str, Any]:
        if role not in ASSIGNABLE_WORKSPACE_ROLES:
            raise ValueError("invalid workspace role")

        record = {
            "workspace_id": workspace_id,
            "operator_id": operator_id,
            "role": role,
            "granted_by": granted_by,
            "granted_at": utc_now_iso(),
        }

        with self._lock:
            self._conn.execute(
                """
                INSERT INTO workspace_roles (
                    workspace_id,
                    operator_id,
                    role,
                    granted_by,
                    granted_at
                ) VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(workspace_id, operator_id)
                DO UPDATE SET
                    role = excluded.role,
                    granted_by = excluded.granted_by,
                    granted_at = excluded.granted_at
                """,
                (
                    record["workspace_id"],
                    record["operator_id"],
                    record["role"],
                    record["granted_by"],
                    record["granted_at"],
                ),
            )
            self._conn.commit()

        return record

    def revoke_role(self, workspace_id: str, operator_id: str) -> None:
        with self._lock:
            self._conn.execute(
                """
                DELETE FROM workspace_roles
                WHERE workspace_id = ? AND operator_id = ?
                """,
                (workspace_id, operator_id),
            )
            self._conn.commit()

    def latest_snapshot(self, workspace_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            row = self._conn.execute(
                """
                SELECT *
                FROM workspace_snapshots
                WHERE workspace_id = ?
                ORDER BY timestamp DESC, id DESC
                LIMIT 1
                """,
                (workspace_id,),
            ).fetchone()

        if row is None:
            return None

        return self._row_to_snapshot(row)

    def get_snapshots(
        self,
        workspace_id: str,
        limit: int = 200,
    ) -> List[Dict[str, Any]]:
        with self._lock:
            rows = self._conn.execute(
                """
                SELECT *
                FROM workspace_snapshots
                WHERE workspace_id = ?
                ORDER BY timestamp DESC, id DESC
                LIMIT ?
                """,
                (workspace_id, limit),
            ).fetchall()

        return [self._row_to_snapshot(row) for row in rows]

    def add_snapshot(
        self,
        workspace: Dict[str, Any],
        state: Dict[str, Any],
        actor_id: str,
        snapshot_type: str,
    ) -> Dict[str, Any]:
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
            "payload": {
                "workspace": workspace,
                "state": state,
            },
        }

        with self._lock:
            self._conn.execute(
                """
                INSERT INTO workspace_snapshots (
                    id,
                    workspace_id,
                    version,
                    snapshot_type,
                    actor_id,
                    timestamp,
                    content_hash,
                    previous_hash,
                    snapshot_hash,
                    payload
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    snapshot["id"],
                    snapshot["workspace_id"],
                    snapshot["version"],
                    snapshot["snapshot_type"],
                    snapshot["actor_id"],
                    snapshot["timestamp"],
                    snapshot["content_hash"],
                    snapshot["previous_hash"],
                    snapshot["snapshot_hash"],
                    json.dumps(snapshot["payload"], sort_keys=True, default=str),
                ),
            )
            self._conn.commit()

        return snapshot

    def add_audit_chain(
        self,
        workspace_id: str,
        actor_id: str,
        action: str,
        details: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        previous = self.latest_audit_chain(workspace_id)
        previous_hash = previous["audit_hash"] if previous else None

        timestamp = utc_now_iso()

        audit_payload = {
            "workspace_id": workspace_id,
            "actor_id": actor_id,
            "action": action,
            "timestamp": timestamp,
            "details": details or {},
            "previous_hash": previous_hash,
        }

        audit_hash = sha256_hex(canonical_json(audit_payload))

        record = {
            "id": generate_audit_chain_id(),
            "workspace_id": workspace_id,
            "actor_id": actor_id,
            "action": action,
            "timestamp": timestamp,
            "details": details or {},
            "previous_hash": previous_hash,
            "audit_hash": audit_hash,
        }

        with self._lock:
            self._conn.execute(
                """
                INSERT INTO workspace_audit_chain (
                    id,
                    workspace_id,
                    actor_id,
                    action,
                    timestamp,
                    details,
                    previous_hash,
                    audit_hash
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    record["id"],
                    record["workspace_id"],
                    record["actor_id"],
                    record["action"],
                    record["timestamp"],
                    json.dumps(record["details"], sort_keys=True, default=str),
                    record["previous_hash"],
                    record["audit_hash"],
                ),
            )
            self._conn.commit()

        return record

    def latest_audit_chain(self, workspace_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            row = self._conn.execute(
                """
                SELECT *
                FROM workspace_audit_chain
                WHERE workspace_id = ?
                ORDER BY timestamp DESC, id DESC
                LIMIT 1
                """,
                (workspace_id,),
            ).fetchone()

        if row is None:
            return None

        return self._row_to_audit_chain(row)

    def get_audit_chain(
        self,
        workspace_id: str,
        limit: int = 200,
    ) -> List[Dict[str, Any]]:
        with self._lock:
            rows = self._conn.execute(
                """
                SELECT *
                FROM workspace_audit_chain
                WHERE workspace_id = ?
                ORDER BY timestamp DESC, id DESC
                LIMIT ?
                """,
                (workspace_id, limit),
            ).fetchall()

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
            "id": row["id"],
            "workspace_id": row["workspace_id"],
            "version": row["version"],
            "snapshot_type": row["snapshot_type"],
            "actor_id": row["actor_id"],
            "timestamp": row["timestamp"],
            "content_hash": row["content_hash"],
            "previous_hash": row["previous_hash"],
            "snapshot_hash": row["snapshot_hash"],
            "payload": json.loads(row["payload"]),
        }

    def _row_to_audit_chain(self, row: sqlite3.Row) -> Dict[str, Any]:
        return {
            "id": row["id"],
            "workspace_id": row["workspace_id"],
            "actor_id": row["actor_id"],
            "action": row["action"],
            "timestamp": row["timestamp"],
            "details": json.loads(row["details"]),
            "previous_hash": row["previous_hash"],
            "audit_hash": row["audit_hash"],
        }
```

---

# 4. Backend: governed workspace service

Create:

**`observatory/backend/workspace_governance_service.py`**

```python
from __future__ import annotations

from typing import Any, Dict, List

from .workspace_governance import (
    ASSIGNABLE_WORKSPACE_ROLES,
    OperatorIdentity,
    WorkspaceActionDenied,
    WorkspaceGovernor,
    WorkspaceSecretDetected,
    scan_workspace_payload,
)
from .workspace_governance_store import WorkspaceGovernanceStore
from .workspace_service import WorkspaceService, WorkspaceRequestValidationError
from .workspace_store import WorkspaceNotFound, WorkspacePermissionDenied


class GovernedWorkspaceService:
    def __init__(
        self,
        base: WorkspaceService,
        governance_store: WorkspaceGovernanceStore,
        governor: WorkspaceGovernor,
    ) -> None:
        self.base = base
        self.governance_store = governance_store
        self.governor = governor

    def create_workspace(
        self,
        actor: Dict[str, Any],
        payload: Dict[str, Any],
    ) -> Dict[str, Any]:
        identity = OperatorIdentity.from_actor(actor)

        decision = self.governor.authorize_create(identity)

        if not decision.allowed:
            raise WorkspacePermissionDenied(decision.reason)

        try:
            scan_workspace_payload(payload)
        except WorkspaceSecretDetected as exc:
            raise WorkspaceRequestValidationError(str(exc)) from exc

        workspace = self.base.create_workspace(actor, payload)

        state = self.governance_store.ensure_governance_state(
            workspace["id"],
            workspace["owner_id"],
        )

        self.governance_store.add_snapshot(
            workspace,
            state,
            actor["id"],
            "created",
        )

        self.governance_store.add_audit_chain(
            workspace["id"],
            actor["id"],
            "workspace_created",
            {
                "name": workspace["name"],
                "visibility": workspace["visibility"],
            },
        )

        return workspace

    def get_workspace(
        self,
        actor: Dict[str, Any],
        workspace_id: str,
    ) -> Dict[str, Any]:
        workspace, _state, _roles, _identity = self._authorize(
            actor,
            workspace_id,
            "read",
        )

        return workspace

    def list_workspaces(self, actor: Dict[str, Any]) -> List[Dict[str, Any]]:
        base_workspaces = self.base.list_workspaces(actor)
        identity = OperatorIdentity.from_actor(actor)

        readable: List[Dict[str, Any]] = []

        for workspace in base_workspaces:
            state = self.governance_store.get_governance_state(workspace["id"])
            roles = self.governance_store.get_roles(workspace["id"])

            decision = self.governor.authorize_action(
                identity,
                workspace,
                state,
                "read",
                roles,
            )

            if decision.allowed:
                readable.append(workspace)

        return readable

    def update_workspace(
        self,
        actor: Dict[str, Any],
        workspace_id: str,
        payload: Dict[str, Any],
    ) -> Dict[str, Any]:
        workspace, state, roles, identity = self._authorize(
            actor,
            workspace_id,
            "update",
        )

        try:
            scan_workspace_payload(payload)
        except WorkspaceSecretDetected as exc:
            raise WorkspaceRequestValidationError(str(exc)) from exc

        updated = self.base.update_workspace(actor, workspace_id, payload)

        refreshed_state = self.governance_store.get_governance_state(workspace_id)

        self.governance_store.add_snapshot(
            updated,
            refreshed_state,
            actor["id"],
            "updated",
        )

        self.governance_store.add_audit_chain(
            workspace_id,
            actor["id"],
            "workspace_updated",
            {
                "updated_fields": sorted(payload.keys()),
            },
        )

        return updated

    def delete_workspace(
        self,
        actor: Dict[str, Any],
        workspace_id: str,
    ) -> Dict[str, Any]:
        workspace, state, roles, identity = self._authorize(
            actor,
            workspace_id,
            "delete",
        )

        deleted = self.base.delete_workspace(actor, workspace_id)

        self.governance_store.add_snapshot(
            deleted,
            state,
            actor["id"],
            "deleted",
        )

        self.governance_store.add_audit_chain(
            workspace_id,
            actor["id"],
            "workspace_deleted",
            {
                "name": deleted["name"],
            },
        )

        return deleted

    def export_workspace(
        self,
        actor: Dict[str, Any],
        workspace_id: str,
    ) -> Dict[str, Any]:
        workspace, state, roles, identity = self._authorize(
            actor,
            workspace_id,
            "export",
        )

        exported = self.base.export_workspace(actor, workspace_id)

        self.governance_store.add_audit_chain(
            workspace_id,
            actor["id"],
            "workspace_exported",
            {
                "bundle_version": exported.get("bundle_version"),
            },
        )

        return exported

    def get_audit(
        self,
        actor: Dict[str, Any],
        workspace_id: str,
        limit: int = 200,
    ) -> Dict[str, Any]:
        workspace, state, roles, identity = self._authorize(
            actor,
            workspace_id,
            "audit",
        )

        base_audit = self.base.get_audit(actor, workspace_id, limit)
        audit_chain = self.governance_store.get_audit_chain(workspace_id, limit)
        snapshots = self.governance_store.get_snapshots(workspace_id, limit)

        return {
            "workspace_id": workspace_id,
            "governance_state": state,
            "audit": base_audit,
            "audit_chain": audit_chain,
            "snapshots": snapshots,
        }

    def grant_role(
        self,
        actor: Dict[str, Any],
        workspace_id: str,
        operator_id: str,
        role: str,
    ) -> Dict[str, Any]:
        workspace, state, roles, identity = self._authorize(
            actor,
            workspace_id,
            "grant_role",
        )

        if role not in ASSIGNABLE_WORKSPACE_ROLES:
            raise WorkspaceRequestValidationError("invalid workspace role")

        if operator_id == workspace["owner_id"]:
            raise WorkspaceRequestValidationError("cannot reassign owner role")

        record = self.governance_store.grant_role(
            workspace_id,
            operator_id,
            role,
            actor["id"],
        )

        self.governance_store.add_audit_chain(
            workspace_id,
            actor["id"],
            "workspace_role_granted",
            {
                "operator_id": operator_id,
                "role": role,
            },
        )

        return record

    def revoke_role(
        self,
        actor: Dict[str, Any],
        workspace_id: str,
        operator_id: str,
    ) -> Dict[str, Any]:
        workspace, state, roles, identity = self._authorize(
            actor,
            workspace_id,
            "revoke_role",
        )

        if operator_id == workspace["owner_id"]:
            raise WorkspaceRequestValidationError("cannot revoke owner role")

        self.governance_store.revoke_role(workspace_id, operator_id)

        self.governance_store.add_audit_chain(
            workspace_id,
            actor["id"],
            "workspace_role_revoked",
            {
                "operator_id": operator_id,
            },
        )

        return {
            "workspace_id": workspace_id,
            "operator_id": operator_id,
            "status": "revoked",
        }

    def _authorize(
        self,
        actor: Dict[str, Any],
        workspace_id: str,
        action: str,
    ):
        workspace = self.base.workspace_store.get_workspace(workspace_id)

        if workspace is None:
            raise WorkspaceNotFound(workspace_id)

        state = self.governance_store.get_governance_state(workspace_id)
        roles = self.governance_store.get_roles(workspace_id)
        identity = OperatorIdentity.from_actor(actor)

        decision = self.governor.authorize_action(
            identity,
            workspace,
            state,
            action,
            roles,
        )

        if not decision.allowed:
            raise WorkspacePermissionDenied(decision.reason)

        return workspace, state, roles, identity
```

---

# 5. Backend: update workspace dependencies

Update:

**`observatory/backend/workspaces_routes.py`**

Add imports:

```python
from .workspace_governance import WorkspaceGovernor
from .workspace_governance_service import GovernedWorkspaceService
from .workspace_governance_store import WorkspaceGovernanceStore
```

Update `require_workspace_actor` so it includes roles:

```python
def require_workspace_actor(request: Request) -> dict[str, str]:
    if not workspaces_enabled():
        raise HTTPException(status_code=403, detail="workspaces_disabled")

    actor_id = request.headers.get("x-operator-id") or request.headers.get("x-actor-id")
    role = (
        request.headers.get("x-operator-role")
        or request.headers.get("x-actor-role")
        or "observer"
    )
    clearance = (
        request.headers.get("x-operator-clearance")
        or request.headers.get("x-actor-clearance")
        or role
    )

    if not actor_id:
        raise HTTPException(status_code=401, detail="operator_id_required")

    token = request.headers.get("x-observatory-token")
    expected_token = os.getenv("OBSERVATORY_API_TOKEN")

    if expected_token:
        if token != expected_token:
            raise HTTPException(status_code=401, detail="invalid_token")
    elif not allow_insecure_local():
        raise HTTPException(
            status_code=403,
            detail="workspace_auth_not_configured",
        )

    roles_header = request.headers.get("x-operator-roles", "")
    roles = [item.strip() for item in roles_header.split(",") if item.strip()]

    if not roles:
        roles = [role]

    return {
        "id": actor_id,
        "role": role,
        "clearance": clearance,
        "roles": roles,
        "auth_method": "trusted-proxy",
    }
```

Replace `get_workspace_service`:

```python
def get_workspace_service(request: Request) -> GovernedWorkspaceService:
    workspace_store: SqliteWorkspaceStore = request.app.state.workspace_store
    governance_store: WorkspaceGovernanceStore = (
        request.app.state.workspace_governance_store
    )
    event_store = request.app.state.gateway.store

    base_service = WorkspaceService(workspace_store, event_store)
    governor = WorkspaceGovernor()

    return GovernedWorkspaceService(base_service, governance_store, governor)
```

Add role endpoints:

```python
class RoleGrantRequest(BaseModel):
    operator_id: str
    role: str


@router.post("/{workspace_id}/roles")
async def grant_workspace_role(
    workspace_id: str,
    payload: RoleGrantRequest,
    actor: dict[str, str] = Depends(require_workspace_actor),
    service: GovernedWorkspaceService = Depends(get_workspace_service),
):
    try:
        return await asyncio.to_thread(
            service.grant_role,
            actor,
            workspace_id,
            payload.operator_id,
            payload.role,
        )
    except WorkspaceNotFound as exc:
        raise HTTPException(status_code=404, detail="workspace_not_found") from exc
    except WorkspacePermissionDenied as exc:
        raise HTTPException(status_code=403, detail="workspace_access_denied") from exc
    except WorkspaceRequestValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.delete("/{workspace_id}/roles/{operator_id}")
async def revoke_workspace_role(
    workspace_id: str,
    operator_id: str,
    actor: dict[str, str] = Depends(require_workspace_actor),
    service: GovernedWorkspaceService = Depends(get_workspace_service),
):
    try:
        return await asyncio.to_thread(
            service.revoke_role,
            actor,
            workspace_id,
            operator_id,
        )
    except WorkspaceNotFound as exc:
        raise HTTPException(status_code=404, detail="workspace_not_found") from exc
    except WorkspacePermissionDenied as exc:
        raise HTTPException(status_code=403, detail="workspace_access_denied") from exc
    except WorkspaceRequestValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
```

Update the audit route to return the governed audit bundle:

```python
@router.get("/{workspace_id}/audit")
async def get_workspace_audit(
    workspace_id: str,
    limit: int = 200,
    actor: dict[str, str] = Depends(require_workspace_actor),
    service: GovernedWorkspaceService = Depends(get_workspace_service),
):
    try:
        return await asyncio.to_thread(
            service.get_audit,
            actor,
            workspace_id,
            limit,
        )
    except WorkspaceNotFound as exc:
        raise HTTPException(status_code=404, detail="workspace_not_found") from exc
    except WorkspacePermissionDenied as exc:
        raise HTTPException(status_code=403, detail="workspace_access_denied") from exc
```

---

# 6. Backend: wire the governance store

Update:

**`observatory/backend/main.py`**

Add import:

```python
from .workspace_governance_store import WorkspaceGovernanceStore
```

Inside `create_app`, after workspace store initialization:

```python
    workspace_governance_store = WorkspaceGovernanceStore(settings.db_path)
    workspace_governance_store.init()

    app.state.workspace_governance_store = workspace_governance_store
```

---

# 7. Trusted proxy identity headers

The frontend proxy should send these headers to the backend:

```text
X-Operator-Id
X-Operator-Role
X-Operator-Clearance
X-Operator-Roles
X-Observatory-Token
```

Example:

```text
X-Operator-Id: operator-01
X-Operator-Role: operator
X-Operator-Clearance: operator
X-Operator-Roles: workspace_creator
X-Observatory-Token: <backend token>
```

For an auditor:

```text
X-Operator-Id: auditor-01
X-Operator-Role: auditor
X-Operator-Clearance: auditor
X-Operator-Roles: global_auditor
```

For an administrator:

```text
X-Operator-Id: admin-01
X-Operator-Role: admin
X-Operator-Clearance: admin
X-Operator-Roles: global_workspace_admin,workspace_creator
```

The browser must never receive the backend token.

---

# 8. Frontend proxy update

Update:

**`observatory/frontend/app/api/workspaces/[[...path]]/route.ts`**

In the header construction block, add roles:

```typescript
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    "X-Operator-Id": session.sub,
    "X-Operator-Role": session.role,
    "X-Operator-Clearance": session.clearance,
    "X-Operator-Roles": session.clearance === "admin"
      ? "global_workspace_admin,workspace_creator"
      : session.clearance === "auditor"
        ? "global_auditor"
        : "workspace_creator"
  };
```

For production, replace this mapping with real group/role claims from OIDC.

---

# 9. What this hardening establishes

After this batch, workspaces have:

```text
operator identity context
explicit action authorization
role-based workspace access
lifecycle enforcement
sensitivity-based export restriction
approval fail-closed behavior
secret scanning
immutable snapshot chain
tamper-evident audit chain
governed role grants
governed role revocations
export auditing
```

The workspace subsystem is now a governed operational artifact rather than a simple saved-search mechanism.

---

# 10. Verification checklist

Before treating hardened workspaces as production-ready, verify:

```text
anonymous operator cannot create workspace
observer cannot create workspace
operator with workspace_creator can create workspace
workspace_denied role blocks all actions
owner can read/update/delete/share/export/audit
viewer can read only
auditor can read/audit/export
contributor can read/update/export but not delete or share
admin can manage roles but not delete unless owner
global_workspace_admin can administer non-owner workspaces
global_workspace_admin cannot delete unless owner
global_auditor can audit all readable workspaces
private workspace is hidden from non-owner
shared workspace grants viewer access
public workspace is readable by authenticated operators
locked workspace blocks update/delete/share
archived workspace blocks update/delete/share
immutable workspace blocks mutation
requires_approval blocks mutation and export
restricted/confidential workspace blocks export for low-privilege roles
secret-shaped workspace payload is rejected
snapshot chain links previous hash
audit chain links previous hash
role grant requires share/grant_role permission
role revoke requires revoke_role permission
owner role cannot be revoked
owner role cannot be reassigned through role grant
audit endpoint returns governance state, snapshots, and audit chain
export emits audit event and audit-chain record
```

---

# 11. Remaining governance extensions

The next hardening layer should add:

```text
OIDC-backed operator identity
real group/role claims
approval records
approval workflows
workspace certification
workspace lock/unlock API
workspace archive/restore API
retention policies
workspace quotas
secret-scan allowlist governance
immutable export bundles
workspace diffing
workspace policy snapshots
```

Those should be introduced only when the operational process requires them.

The foundation is now strong enough to support those extensions without redesigning the workspace subsystem.