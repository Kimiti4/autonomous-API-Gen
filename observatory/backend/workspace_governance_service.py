"""Governed workspace service: policy-enforced wrapper over the base service.

Every mutating path passes secret scanning, governance authorization,
snapshot capture, and audit-chain recording. Reads pass authorization.
The base service remains the CRUD engine; this layer adds governance.
"""
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
from .workspaces_store import WorkspaceNotFound, WorkspacePermissionDenied


class GovernedWorkspaceService:
    def __init__(self, base: WorkspaceService,
                 governance_store: WorkspaceGovernanceStore,
                 governor: WorkspaceGovernor) -> None:
        self.base = base
        self.governance_store = governance_store
        self.governor = governor

    def create_workspace(self, actor: Dict[str, Any],
                         payload: Dict[str, Any]) -> Dict[str, Any]:
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
            workspace["id"], workspace["owner_id"])
        self.governance_store.add_snapshot(workspace, state, actor["id"],
                                           "created")
        self.governance_store.add_audit_chain(
            workspace["id"], actor["id"], "workspace_created",
            {"name": workspace["name"],
             "visibility": workspace["visibility"]})
        return workspace

    def get_workspace(self, actor: Dict[str, Any],
                      workspace_id: str) -> Dict[str, Any]:
        workspace, _state, _roles, _identity = self._authorize(
            actor, workspace_id, "read")
        return workspace

    def list_workspaces(self, actor: Dict[str, Any]) -> List[Dict[str, Any]]:
        base_workspaces = self.base.list_workspaces(actor)
        identity = OperatorIdentity.from_actor(actor)
        readable: List[Dict[str, Any]] = []
        for workspace in base_workspaces:
            state = self.governance_store.get_governance_state(workspace["id"])
            roles = self.governance_store.get_roles(workspace["id"])
            decision = self.governor.authorize_action(
                identity, workspace, state, "read", roles)
            if decision.allowed:
                readable.append(workspace)
        return readable

    def update_workspace(self, actor: Dict[str, Any], workspace_id: str,
                         payload: Dict[str, Any]) -> Dict[str, Any]:
        workspace, state, roles, identity = self._authorize(
            actor, workspace_id, "update")
        try:
            scan_workspace_payload(payload)
        except WorkspaceSecretDetected as exc:
            raise WorkspaceRequestValidationError(str(exc)) from exc
        # Role-authorized mutation uses the persistence-only path: the
        # base owner gate cannot express contributor/admin delegation, and
        # authorization was already decided by policy above.
        from .workspace_service import validate_workspace_payload
        normalized = validate_workspace_payload(payload, partial=True)
        if normalized.get("visibility") == "shared":
            existing = self.base.workspace_store.get_workspace(workspace_id)
            assert existing is not None
            shared_with = normalized.get("shared_with",
                                         existing["shared_with"])
            if not shared_with:
                from .workspace_service import (
                    WorkspaceRequestValidationError as ValidationError)
                raise ValidationError(
                    "shared workspaces require at least one shared_with "
                    "operator")
            normalized["shared_with"] = shared_with
        updated = self.base.workspace_store.apply_update(
            workspace_id, normalized)
        refreshed_state = self.governance_store.get_governance_state(
            workspace_id)
        self.governance_store.add_snapshot(updated, refreshed_state,
                                           actor["id"], "updated")
        self.governance_store.add_audit_chain(
            workspace_id, actor["id"], "workspace_updated",
            {"updated_fields": sorted(payload.keys())})
        return updated

    def delete_workspace(self, actor: Dict[str, Any],
                         workspace_id: str) -> Dict[str, Any]:
        workspace, state, roles, identity = self._authorize(
            actor, workspace_id, "delete")
        deleted = self.base.delete_workspace(actor, workspace_id)
        self.governance_store.add_snapshot(deleted, state, actor["id"],
                                           "deleted")
        self.governance_store.add_audit_chain(
            workspace_id, actor["id"], "workspace_deleted",
            {"name": deleted["name"]})
        return deleted

    def export_workspace(self, actor: Dict[str, Any],
                         workspace_id: str) -> Dict[str, Any]:
        workspace, state, roles, identity = self._authorize(
            actor, workspace_id, "export")
        exported = self.base.export_workspace(actor, workspace_id)
        self.governance_store.add_audit_chain(
            workspace_id, actor["id"], "workspace_exported",
            {"bundle_version": exported.get("bundle_version")})
        return exported

    def get_audit(self, actor: Dict[str, Any], workspace_id: str,
                  limit: int = 200) -> Dict[str, Any]:
        workspace, state, roles, identity = self._authorize(
            actor, workspace_id, "audit")
        base_audit = self.base.get_audit(actor, workspace_id, limit)
        audit_chain = self.governance_store.get_audit_chain(
            workspace_id, limit)
        snapshots = self.governance_store.get_snapshots(workspace_id, limit)
        return {"workspace_id": workspace_id,
                "governance_state": state,
                "audit": base_audit,
                "audit_chain": audit_chain,
                "snapshots": snapshots}

    def grant_role(self, actor: Dict[str, Any], workspace_id: str,
                   operator_id: str, role: str) -> Dict[str, Any]:
        workspace, state, roles, identity = self._authorize(
            actor, workspace_id, "grant_role")
        if role not in ASSIGNABLE_WORKSPACE_ROLES:
            raise WorkspaceRequestValidationError("invalid workspace role")
        if operator_id == workspace["owner_id"]:
            raise WorkspaceRequestValidationError(
                "cannot reassign owner role")
        record = self.governance_store.grant_role(
            workspace_id, operator_id, role, actor["id"])
        self.governance_store.add_audit_chain(
            workspace_id, actor["id"], "workspace_role_granted",
            {"operator_id": operator_id, "role": role})
        return record

    def revoke_role(self, actor: Dict[str, Any], workspace_id: str,
                    operator_id: str) -> Dict[str, Any]:
        workspace, state, roles, identity = self._authorize(
            actor, workspace_id, "revoke_role")
        if operator_id == workspace["owner_id"]:
            raise WorkspaceRequestValidationError("cannot revoke owner role")
        self.governance_store.revoke_role(workspace_id, operator_id)
        self.governance_store.add_audit_chain(
            workspace_id, actor["id"], "workspace_role_revoked",
            {"operator_id": operator_id})
        return {"workspace_id": workspace_id, "operator_id": operator_id,
                "status": "revoked"}

    def _authorize(self, actor: Dict[str, Any], workspace_id: str,
                   action: str):
        workspace = self.base.workspace_store.get_workspace(workspace_id)
        if workspace is None:
            raise WorkspaceNotFound(workspace_id)
        state = self.governance_store.get_governance_state(workspace_id)
        roles = self.governance_store.get_roles(workspace_id)
        identity = OperatorIdentity.from_actor(actor)
        decision = self.governor.authorize_action(
            identity, workspace, state, action, roles)
        if not decision.allowed:
            raise WorkspacePermissionDenied(decision.reason)
        return workspace, state, roles, identity
