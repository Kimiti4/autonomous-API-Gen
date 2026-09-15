"""Workspace service: validation, visibility scoping, audit, event emission.

Ownership is enforced here for mutation; visibility scoping for reads.
Finer-grained roles/lifecycle live in the governance layer
(workspace_governance_service.py), which wraps this service.
"""
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


def _clean_string(value: Any, field: str, max_length: int = 500,
                  required: bool = False) -> Optional[str]:
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
        raise WorkspaceRequestValidationError(
            f"{field} exceeds maximum length")
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
        query.get("categories"), "query.categories")
    normalized["severities"] = _clean_string_list(
        query.get("severities"), "query.severities")
    normalized["epistemic_statuses"] = _clean_string_list(
        query.get("epistemic_statuses"), "query.epistemic_statuses")
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
        raise WorkspaceRequestValidationError(
            "query.limit must be an integer") from exc
    if limit < 1 or limit > 1000:
        raise WorkspaceRequestValidationError(
            "query.limit must be between 1 and 1000")
    normalized["limit"] = limit
    return normalized


def validate_workspace_payload(payload: Any,
                               partial: bool = False) -> Dict[str, Any]:
    if not isinstance(payload, dict):
        raise WorkspaceRequestValidationError(
            "workspace payload must be an object")
    normalized: Dict[str, Any] = {}
    if not partial or "name" in payload:
        normalized["name"] = _clean_string(
            payload.get("name"), "name", max_length=200, required=not partial)
    if not partial or "description" in payload:
        normalized["description"] = _clean_string(
            payload.get("description"), "description",
            max_length=2000) or ""
    if not partial or "visibility" in payload:
        visibility = _clean_string(
            payload.get("visibility"), "visibility", max_length=20,
            required=not partial)
        if visibility not in ALLOWED_VISIBILITIES:
            raise WorkspaceRequestValidationError(
                "visibility must be private, shared, or public")
        normalized["visibility"] = visibility
    if not partial or "shared_with" in payload:
        normalized["shared_with"] = _clean_string_list(
            payload.get("shared_with"), "shared_with")
    if not partial or "tags" in payload:
        normalized["tags"] = _clean_string_list(payload.get("tags"), "tags")
    if not partial or "query" in payload:
        if "query" not in payload and partial:
            pass
        else:
            normalized["query"] = validate_query(payload.get("query"))
    if not partial:
        if normalized.get("visibility") == "shared" and not normalized.get(
                "shared_with"):
            raise WorkspaceRequestValidationError(
                "shared workspaces require at least one shared_with operator")
    return normalized


def can_read_workspace(workspace: Dict[str, Any], actor_id: str) -> bool:
    if workspace["owner_id"] == actor_id:
        return True
    if workspace["visibility"] == "public":
        return True
    if workspace["visibility"] == "shared" and actor_id in workspace.get(
            "shared_with", []):
        return True
    return False


class WorkspaceService:
    def __init__(self, workspace_store: SqliteWorkspaceStore,
                 event_store: Any) -> None:
        self.workspace_store = workspace_store
        self.event_store = event_store

    def create_workspace(self, actor: Dict[str, str],
                         payload: Dict[str, Any]) -> Dict[str, Any]:
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
            created["id"], actor["id"], "workspace_created",
            {"name": created["name"],
             "visibility": created["visibility"]})
        self._emit_event("created", created, actor)
        return created

    def get_workspace(self, actor: Dict[str, str],
                      workspace_id: str) -> Dict[str, Any]:
        workspace = self.workspace_store.get_workspace(workspace_id)
        if workspace is None:
            raise WorkspaceNotFound(workspace_id)
        if not can_read_workspace(workspace, actor["id"]):
            raise WorkspacePermissionDenied(workspace_id)
        return workspace

    def list_workspaces(self, actor: Dict[str, str]) -> List[Dict[str, Any]]:
        return [workspace for workspace in
                self.workspace_store.list_workspaces()
                if can_read_workspace(workspace, actor["id"])]

    def update_workspace(self, actor: Dict[str, str], workspace_id: str,
                         payload: Dict[str, Any]) -> Dict[str, Any]:
        existing = self.workspace_store.get_workspace(workspace_id)
        if existing is None:
            raise WorkspaceNotFound(workspace_id)
        if existing["owner_id"] != actor["id"]:
            raise WorkspacePermissionDenied(workspace_id)
        normalized = validate_workspace_payload(payload, partial=True)
        if normalized.get("visibility") == "shared":
            shared_with = normalized.get("shared_with",
                                         existing["shared_with"])
            if not shared_with:
                raise WorkspaceRequestValidationError(
                    "shared workspaces require at least one shared_with "
                    "operator")
            normalized["shared_with"] = shared_with
        updated = self.workspace_store.update_workspace(
            workspace_id, actor["id"], normalized)
        self.workspace_store.add_audit(
            workspace_id, actor["id"], "workspace_updated",
            {"updated_fields": sorted(normalized.keys())})
        self._emit_event("updated", updated, actor)
        return updated

    def delete_workspace(self, actor: Dict[str, str],
                         workspace_id: str) -> Dict[str, Any]:
        deleted = self.workspace_store.delete_workspace(workspace_id,
                                                         actor["id"])
        self.workspace_store.add_audit(
            workspace_id, actor["id"], "workspace_deleted",
            {"name": deleted["name"]})
        self._emit_event("deleted", deleted, actor)
        return deleted

    def export_workspace(self, actor: Dict[str, str],
                         workspace_id: str) -> Dict[str, Any]:
        workspace = self.get_workspace(actor, workspace_id)
        self.workspace_store.add_audit(
            workspace_id, actor["id"], "workspace_exported", {})
        self._emit_event("exported", workspace, actor)
        return {"bundle_version": "observatory-workspace-export-v1",
                "workspace": workspace,
                "exported_by": actor["id"],
                "exported_at": utc_now_iso()}

    def get_audit(self, actor: Dict[str, str], workspace_id: str,
                  limit: int = 200) -> List[Dict[str, Any]]:
        self.get_workspace(actor, workspace_id)
        return self.workspace_store.get_audit(workspace_id, limit)

    def _emit_event(self, action: str, workspace: Dict[str, Any],
                    actor: Dict[str, str]) -> None:
        event = new_event(
            category=EventCategory.KNOWLEDGE,
            type=f"workspace_{action}",
            subject_id=workspace["id"],
            source="observatory.workspaces",
            payload={"workspace_id": workspace["id"],
                     "workspace_name": workspace["name"],
                     "owner_id": workspace["owner_id"],
                     "visibility": workspace["visibility"],
                     "action": action, "actor_id": actor["id"],
                     "summary": f"Workspace {workspace['name']} {action}"},
            epistemic_status=EpistemicStatus.OBSERVED,
            severity="info")
        self.event_store.append(event)
