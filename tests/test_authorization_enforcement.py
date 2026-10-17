"""Adversarial tests for the pure TaskFlow authorization primitives."""
import pytest

from tiannara.domain.models.authorization_enforcement import (
    AuthenticatedPrincipal,
    AuthorizationDenied,
    WorkspaceMembership,
    WorkspaceRole,
    require_owner_for_permanent_workspace_deletion,
    require_privileged_role_change,
    require_role,
    require_same_workspace,
    require_workspace_membership,
)


def _membership(subject="alice", workspace="w1", role=WorkspaceRole.MEMBER, active=True):
    return WorkspaceMembership(subject, workspace, role, active)


def _lookup(rows):
    return lambda subject, workspace: rows.get((subject, workspace))


def test_membership_must_be_active_and_match_actor_and_workspace():
    principal = AuthenticatedPrincipal("alice")
    lookup = _lookup({("alice", "w1"): _membership()})
    assert require_workspace_membership(principal, "w1", lookup).subject_id == "alice"

    with pytest.raises(AuthorizationDenied):
        require_workspace_membership(principal, "w2", lookup)
    with pytest.raises(AuthorizationDenied):
        require_workspace_membership(
            principal, "w1",
            _lookup({("alice", "w1"): _membership(active=False)}),
        )


def test_membership_lookup_cannot_return_another_actors_or_workspaces_row():
    with pytest.raises(AuthorizationDenied):
        require_workspace_membership(
            AuthenticatedPrincipal("alice"), "w1",
            lambda _subject, _workspace: _membership(subject="mallory", workspace="w2"),
        )


def test_resource_scope_rejects_foreign_or_missing_workspace_without_disclosure():
    membership = _membership(workspace="w1")
    require_same_workspace(membership, "w1")
    for foreign_scope in ("w2", None, ""):
        with pytest.raises(AuthorizationDenied, match="resource unavailable"):
            require_same_workspace(membership, foreign_scope)


def test_role_checks_fail_closed_for_disallowed_roles():
    require_role(_membership(role=WorkspaceRole.OWNER), {WorkspaceRole.OWNER})
    with pytest.raises(AuthorizationDenied):
        require_role(_membership(role=WorkspaceRole.MEMBER), {WorkspaceRole.OWNER})


def test_permanent_workspace_deletion_requires_owner_and_all_safeguards():
    owner = _membership(role=WorkspaceRole.OWNER)
    require_owner_for_permanent_workspace_deletion(
        owner,
        explicit_confirmation=True,
        ownership_verified=True,
        audit_evidence_recorded=True,
    )
    for safeguard in (
        {"explicit_confirmation": False, "ownership_verified": True, "audit_evidence_recorded": True},
        {"explicit_confirmation": True, "ownership_verified": False, "audit_evidence_recorded": True},
        {"explicit_confirmation": True, "ownership_verified": True, "audit_evidence_recorded": False},
    ):
        with pytest.raises(AuthorizationDenied):
            require_owner_for_permanent_workspace_deletion(owner, **safeguard)
    with pytest.raises(AuthorizationDenied):
        require_owner_for_permanent_workspace_deletion(
            _membership(role=WorkspaceRole.MANAGER),
            explicit_confirmation=True,
            ownership_verified=True,
            audit_evidence_recorded=True,
        )


def test_manager_cannot_change_owner_or_manager_roles():
    manager = _membership(role=WorkspaceRole.MANAGER)
    with pytest.raises(AuthorizationDenied):
        require_privileged_role_change(manager, WorkspaceRole.OWNER)
    with pytest.raises(AuthorizationDenied):
        require_privileged_role_change(manager, WorkspaceRole.MANAGER)
    require_privileged_role_change(manager, WorkspaceRole.MEMBER)


def test_member_cannot_change_any_role_and_inactive_membership_is_denied():
    member = _membership(role=WorkspaceRole.MEMBER)
    with pytest.raises(AuthorizationDenied):
        require_privileged_role_change(member, WorkspaceRole.MEMBER)
    with pytest.raises(AuthorizationDenied):
        require_role(_membership(role=WorkspaceRole.OWNER, active=False), {WorkspaceRole.OWNER})
