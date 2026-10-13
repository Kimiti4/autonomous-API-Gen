"""Fail-closed authorization primitives for TaskFlow backend consumers.

These pure policy checks are not a complete authentication/session system and
must not be treated as proof that a generated application consumes them. They
accept an already-authenticated principal and an authoritative membership
lookup supplied by the runtime. Ambiguous operations remain denied.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Callable


class AuthorizationDenied(PermissionError):
    """An actor is not authorized for the requested workspace operation."""


class WorkspaceRole(str, Enum):
    OWNER = "owner"
    MANAGER = "manager"
    MEMBER = "member"


@dataclass(frozen=True)
class AuthenticatedPrincipal:
    """Identity established by a separately verified authentication layer."""

    subject_id: str


@dataclass(frozen=True)
class WorkspaceMembership:
    """Authoritative membership row loaded from the trusted persistence layer."""

    subject_id: str
    workspace_id: str
    role: WorkspaceRole
    active: bool = True


MembershipLookup = Callable[[str, str], WorkspaceMembership | None]


def require_workspace_membership(
    principal: AuthenticatedPrincipal,
    workspace_id: str,
    lookup: MembershipLookup,
) -> WorkspaceMembership:
    """Resolve active membership for this exact actor/workspace pair."""
    if not principal.subject_id or not workspace_id:
        raise AuthorizationDenied("workspace access denied")
    membership = lookup(principal.subject_id, workspace_id)
    if (
        membership is None
        or not membership.active
        or membership.subject_id != principal.subject_id
        or membership.workspace_id != workspace_id
    ):
        # Do not reveal whether a foreign workspace or membership exists.
        raise AuthorizationDenied("workspace access denied")
    return membership


def require_role(
    membership: WorkspaceMembership,
    allowed_roles: set[WorkspaceRole],
) -> None:
    """Require one of the explicitly permitted roles."""
    if not membership.active or membership.role not in allowed_roles:
        raise AuthorizationDenied("operation not permitted")


def require_same_workspace(
    membership: WorkspaceMembership,
    resource_workspace_id: str | None,
) -> None:
    """Reject absent or cross-workspace resource scope without disclosure."""
    if (
        not membership.active
        or not resource_workspace_id
        or resource_workspace_id != membership.workspace_id
    ):
        raise AuthorizationDenied("resource unavailable")


def require_owner_for_permanent_workspace_deletion(
    membership: WorkspaceMembership,
    *,
    explicit_confirmation: bool,
    ownership_verified: bool,
    audit_evidence_recorded: bool,
) -> None:
    """Apply all reviewed deletion safeguards; missing proof fails closed."""
    require_role(membership, {WorkspaceRole.OWNER})
    if not (
        explicit_confirmation
        and ownership_verified
        and audit_evidence_recorded
    ):
        raise AuthorizationDenied("workspace deletion requirements not satisfied")


def require_privileged_role_change(
    actor_membership: WorkspaceMembership,
    target_role: WorkspaceRole,
) -> None:
    """Only the owner may change privileged roles; managers cannot do so."""
    if target_role in {WorkspaceRole.OWNER, WorkspaceRole.MANAGER}:
        require_role(actor_membership, {WorkspaceRole.OWNER})
    elif actor_membership.role not in {WorkspaceRole.OWNER, WorkspaceRole.MANAGER}:
        raise AuthorizationDenied("operation not permitted")
