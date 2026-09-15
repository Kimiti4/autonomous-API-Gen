"""Workspace governance policy engine: roles, lifecycle, sensitivity,
snapshots, tamper-evident audit, secret scanning, approval fail-closed.

Pure policy evaluation (no I/O): authorize_create/authorize_action take
identity + workspace + state + role map and return a decision. Deny is
the default; every allowance names its reason.
"""
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
    "create", "read", "update", "delete", "share", "export", "audit",
    "grant_role", "revoke_role", "lock", "unlock", "archive", "restore",
    "certify",
}

ASSIGNABLE_WORKSPACE_ROLES = {"viewer", "auditor", "contributor", "admin"}

ROLE_PERMISSIONS: Dict[str, Set[str]] = {
    "viewer": {"read"},
    "auditor": {"read", "audit", "export"},
    "contributor": {"read", "update", "export"},
    "admin": {"read", "update", "share", "audit", "export", "grant_role",
              "revoke_role", "lock", "unlock", "archive"},
    "owner": {"read", "update", "delete", "share", "audit", "export",
              "grant_role", "revoke_role", "lock", "unlock", "archive",
              "restore", "certify"},
}

SENSITIVITY_LEVELS = {"general", "restricted", "confidential"}
LIFECYCLE_STATES = {"active", "locked", "archived"}

# NOTE: canonical JSON backslash-escapes quotes, so optional
# backslashes are tolerated around value delimiters (same blind spot
# previously fixed in the D28 secret scanner).
SECRET_PATTERNS = [
    ("aws_access_key_id", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("private_key", re.compile(r"-----BEGIN[A-Z ]*PRIVATE KEY-----")),
    ("json_secret_key", re.compile(
        r'"(password|passwd|secret|token|api_key|session_cookie|private_key'
        r'|credential|authorization)"\s*:\s*"[^"]{4,}"')),
    ("generic_password", re.compile(
        r"(?i)\b(password|passwd|pwd)\b\s*[:=]\s*\\?['\"][^'\"]{8,}")),
    ("generic_secret", re.compile(
        r"(?i)\b(secret|token|api_key|apikey|access_token|refresh_token)\b"
        r"\s*[:=]\s*\\?['\"][^'\"]{16,}")),
    ("bearer_token", re.compile(r"\bBearer\s+[A-Za-z0-9\-._~+/]+=*\b")),
    ("database_url_with_credentials", re.compile(
        r"(?i)\b(postgresql|postgres|mongodb|redis|mysql)\+?://[^:\s]+:[^@\s]+@")),
]


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, default=str)


def sha256_hex(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def workspace_governance_hash(workspace: Dict[str, Any],
                              state: Dict[str, Any]) -> str:
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
                f"secret-shaped material detected: {pattern_name}")


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
        roles = tuple(sorted({str(role) for role in raw_roles
                              if str(role).strip()}))
        if not roles:
            roles = (str(actor.get("role", "observer")),)
        return cls(
            operator_id=str(actor.get("id", "anonymous")),
            roles=roles,
            clearance=str(actor.get("clearance",
                                    actor.get("role", "observer"))),
            auth_method=str(actor.get("auth_method", "unknown")))

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
        if (identity.clearance in {"operator", "architect", "admin"}
                or "workspace_creator" in identity.global_roles
                or "global_workspace_admin" in identity.global_roles):
            return GovernanceDecision(True, "create_allowed")
        return GovernanceDecision(False, "create_not_authorized")

    def effective_role(self, identity: OperatorIdentity,
                       workspace: Dict[str, Any],
                       workspace_roles: Dict[str, str]) -> Optional[str]:
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
        if (workspace["visibility"] == "shared"
                and identity.operator_id in workspace.get("shared_with", [])):
            return "viewer"
        return None

    def authorize_action(self, identity: OperatorIdentity,
                         workspace: Dict[str, Any],
                         state: Dict[str, Any], action: str,
                         workspace_roles: Dict[str, str]) -> GovernanceDecision:
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
                "read", "audit"}:
            return GovernanceDecision(
                False, f"lifecycle_{lifecycle_state}_blocks_action")
        if immutable and action in {
                "update", "delete", "share", "grant_role", "revoke_role",
                "lock", "unlock", "archive", "restore", "certify"}:
            return GovernanceDecision(False, "workspace_immutable")
        if requires_approval and action in {
                "update", "delete", "share", "grant_role", "revoke_role",
                "export", "lock", "unlock", "archive", "restore", "certify"}:
            return GovernanceDecision(False, "approval_required")
        if (sensitivity in {"restricted", "confidential"}
                and action == "export"
                and role not in {"owner", "admin", "auditor"}):
            return GovernanceDecision(False, "sensitivity_blocks_export")
        permissions = ROLE_PERMISSIONS.get(role, set())
        if action not in permissions:
            return GovernanceDecision(False, "role_lacks_permission")
        return GovernanceDecision(True, "allowed")
