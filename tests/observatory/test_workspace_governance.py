"""Workspace governance policy unit tests (pure evaluation, no I/O)."""
from __future__ import annotations

import unittest

from observatory.backend.workspace_governance import (
    OperatorIdentity,
    WorkspaceGovernor,
    scan_workspace_payload,
    workspace_governance_hash,
    WorkspaceSecretDetected,
)


def _identity(operator_id="op-1", roles=(), clearance="operator"):
    return OperatorIdentity(operator_id=operator_id, roles=tuple(roles),
                            clearance=clearance, auth_method="test")


def _workspace(owner="op-1", visibility="private", shared_with=()):
    return {"id": "ws-1", "name": "W", "description": "d",
            "owner_id": owner, "visibility": visibility,
            "shared_with": list(shared_with), "tags": [],
            "query": {"limit": 200}, "version": 1}


def _state(**overrides):
    base = {"sensitivity": "general", "lifecycle_state": "active",
            "requires_approval": False, "immutable": False}
    base.update(overrides)
    return base


class CreatePolicy(unittest.TestCase):
    def setUp(self):
        self.governor = WorkspaceGovernor()

    def test_anonymous_denied(self):
        decision = self.governor.authorize_create(_identity(operator_id=""))
        self.assertFalse(decision.allowed)

    def test_observer_denied(self):
        decision = self.governor.authorize_create(
            _identity(clearance="observer"))
        self.assertFalse(decision.allowed)

    def test_operator_allowed(self):
        self.assertTrue(
            self.governor.authorize_create(_identity()).allowed)

    def test_denied_role_blocks_all(self):
        identity = _identity(roles=("workspace_denied",))
        self.assertFalse(
            self.governor.authorize_create(identity).allowed)
        self.assertFalse(
            self.governor.authorize_action(
                identity, _workspace(), _state(), "read", {}).allowed)


class RoleMatrix(unittest.TestCase):
    def setUp(self):
        self.governor = WorkspaceGovernor()
        self.workspace = _workspace()
        self.state = _state()

    def _can(self, identity, action, roles=None, workspace=None, state=None):
        return self.governor.authorize_action(
            identity, workspace or self.workspace,
            state or self.state, action, roles or {}).allowed

    def test_owner_all(self):
        identity = _identity()
        for action in ("read", "update", "delete", "share", "export", "audit",
                       "grant_role", "revoke_role", "lock", "archive",
                       "restore", "certify"):
            self.assertTrue(self._can(identity, action), action)

    def test_viewer_read_only(self):
        identity = _identity(operator_id="viewer-1")
        roles = {"viewer-1": "viewer"}
        workspace = _workspace(visibility="shared",
                               shared_with=["viewer-1"])
        self.assertTrue(self._can(identity, "read", roles, workspace))
        for action in ("update", "delete", "share", "export", "audit"):
            self.assertFalse(self._can(identity, action, roles, workspace),
                             action)

    def test_auditor_matrix(self):
        identity = _identity(operator_id="aud-1")
        roles = {"aud-1": "auditor"}
        workspace = _workspace(visibility="shared", shared_with=["aud-1"])
        for action in ("read", "audit", "export"):
            self.assertTrue(self._can(identity, action, roles, workspace),
                            action)
        for action in ("update", "delete", "share"):
            self.assertFalse(self._can(identity, action, roles, workspace),
                             action)

    def test_contributor_matrix(self):
        identity = _identity(operator_id="con-1")
        roles = {"con-1": "contributor"}
        workspace = _workspace(visibility="shared", shared_with=["con-1"])
        for action in ("read", "update", "export"):
            self.assertTrue(self._can(identity, action, roles, workspace),
                            action)
        for action in ("delete", "share", "audit"):
            self.assertFalse(self._can(identity, action, roles, workspace),
                             action)

    def test_admin_no_delete_unless_owner(self):
        identity = _identity(operator_id="adm-1")
        roles = {"adm-1": "admin"}
        workspace = _workspace(visibility="shared", shared_with=["adm-1"])
        self.assertTrue(self._can(identity, "grant_role", roles, workspace))
        self.assertFalse(self._can(identity, "delete", roles, workspace))

    def test_global_admin_administered_not_owner(self):
        identity = _identity(operator_id="g-1",
                             roles=("global_workspace_admin",))
        workspace = _workspace(owner="someone-else", visibility="private")
        self.assertTrue(self._can(identity, "grant_role", workspace=workspace))
        self.assertFalse(self._can(identity, "delete", workspace=workspace))

    def test_global_auditor(self):
        identity = _identity(operator_id="ga-1",
                             roles=("global_auditor",))
        workspace = _workspace(owner="someone-else", visibility="private")
        self.assertTrue(self._can(identity, "audit", workspace=workspace))
        self.assertFalse(self._can(identity, "update", workspace=workspace))

    def test_unknown_action_denied(self):
        self.assertFalse(self._can(_identity(), "teleport"))


class LifecycleSensitivity(unittest.TestCase):
    def setUp(self):
        self.governor = WorkspaceGovernor()
        self.identity = _identity()
        self.workspace = _workspace()

    def _can(self, action, state):
        return self.governor.authorize_action(
            self.identity, self.workspace, state, action, {}).allowed

    def test_locked_blocks_mutation(self):
        state = _state(lifecycle_state="locked")
        self.assertTrue(self._can("read", state))
        self.assertTrue(self._can("audit", state))
        for action in ("update", "delete", "share", "export"):
            self.assertFalse(self._can(action, state), action)

    def test_archived_blocks_mutation(self):
        state = _state(lifecycle_state="archived")
        self.assertTrue(self._can("read", state))
        self.assertFalse(self._can("update", state))

    def test_immutable_blocks_mutation(self):
        state = _state(immutable=True)
        self.assertTrue(self._can("read", state))
        self.assertTrue(self._can("export", state))
        for action in ("update", "delete", "certify"):
            self.assertFalse(self._can(action, state), action)

    def test_approval_blocks_mutation_and_export(self):
        state = _state(requires_approval=True)
        self.assertTrue(self._can("read", state))
        for action in ("update", "delete", "export", "share"):
            self.assertFalse(self._can(action, state), action)

    def test_sensitivity_blocks_export(self):
        viewer_workspace = _workspace(visibility="shared",
                                      shared_with=["v-1"])
        viewer = _identity(operator_id="v-1")
        state = _state(sensitivity="restricted")
        self.assertFalse(self.governor.authorize_action(
            viewer, viewer_workspace, state, "export", {}).allowed)
        admin_roles = {"adm-1": "admin"}
        admin = _identity(operator_id="adm-1")
        admin_workspace = _workspace(visibility="shared",
                                     shared_with=["adm-1"])
        self.assertTrue(self.governor.authorize_action(
            admin, admin_workspace, state, "export",
            admin_roles).allowed)


class SecretsAndHash(unittest.TestCase):
    def test_secret_payload_rejected(self):
        with self.assertRaises(WorkspaceSecretDetected):
            from observatory.backend.workspace_governance import (
                scan_workspace_payload)
            scan_workspace_payload(
                {"name": "x", "query": {"q": "password = \"supersecret1\""}})

    def test_clean_payload_passes(self):
        from observatory.backend.workspace_governance import (
            scan_workspace_payload)
        scan_workspace_payload({"name": "Priority trace",
                                "query": {"q": "priority"}})

    def test_governance_hash_stable(self):
        first = workspace_governance_hash(_workspace(), _state())
        second = workspace_governance_hash(_workspace(), _state())
        self.assertEqual(first, second)
        self.assertEqual(len(first), 64)
        changed = workspace_governance_hash(
            _workspace(), _state(sensitivity="restricted"))
        self.assertNotEqual(first, changed)


if __name__ == "__main__":
    unittest.main()
