"""Workspace API tests: auth matrix, CRUD, roles, lifecycle, audit, export.

Each test builds an isolated app (temp DB). The workspace feature flag
and token are set per test; stores are closed before temp cleanup
(Windows file-lock hygiene).
"""
from __future__ import annotations

import os
import tempfile
import unittest

from fastapi.testclient import TestClient

OWNER = {"X-Operator-Id": "op-owner", "X-Actor-Role": "operator",
         "X-Observatory-Token": "test-token"}
OTHER = {"X-Actor-Id": "op-other", "X-Actor-Role": "operator",
         "X-Observatory-Token": "test-token"}
OBSERVER = {"X-Actor-Id": "op-obs", "X-Actor-Role": "observer",
            "X-Observatory-Token": "test-token"}


def _client(testcase: unittest.TestCase, workspaces_enabled: str = "true"):
    import observatory.backend.main as main_module

    tmp = tempfile.TemporaryDirectory()
    testcase.addCleanup(tmp.cleanup)
    os.environ["OBSERVATORY_DB_PATH"] = os.path.join(tmp.name, "obs.sqlite3")
    os.environ["OBSERVATORY_API_TOKEN"] = "test-token"
    os.environ["OBSERVATORY_WORKSPACES_ENABLED"] = workspaces_enabled
    os.environ.pop("OBSERVATORY_WORKSPACES_ALLOW_INSECURE_LOCAL", None)
    main_module.get_settings.cache_clear()
    from observatory.backend.main import create_app
    client = TestClient(create_app())
    stores = [client.app.state.gateway.store,
              client.app.state.workspace_store,
              client.app.state.workspace_governance_store]
    testcase.addCleanup(lambda: [store.close() for store in stores])
    return client


def _payload(**overrides):
    base = {"name": "Trace", "description": "d",
            "query": {"q": "priority", "limit": 50},
            "visibility": "private", "shared_with": [], "tags": []}
    base.update(overrides)
    return base


def _create(client, headers=OWNER, **overrides):
    response = client.post("/observatory/workspaces",
                           json=_payload(**overrides), headers=headers)
    assert response.status_code == 200, response.text
    return response.json()


class DisabledByDefault(unittest.TestCase):
    def test_disabled_returns_403(self):
        client = _client(self, workspaces_enabled="false")
        response = client.post("/observatory/workspaces",
                               json=_payload(), headers=OWNER)
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()["detail"], "workspaces_disabled")

    def test_missing_operator_id_401(self):
        client = _client(self)
        headers = {"X-Actor-Role": "operator",
                   "X-Observatory-Token": "test-token"}
        response = client.post("/observatory/workspaces",
                               json=_payload(), headers=headers)
        self.assertEqual(response.status_code, 401)

    def test_invalid_token_401(self):
        client = _client(self)
        headers = dict(OWNER, **{"X-Observatory-Token": "wrong"})
        response = client.post("/observatory/workspaces",
                               json=_payload(), headers=headers)
        self.assertEqual(response.status_code, 401)


class CrudVisibility(unittest.TestCase):
    def test_create_persists_and_audits(self):
        client = _client(self)
        created = _create(client)
        self.assertEqual(created["version"], 1)
        fetched = client.get(
            f"/observatory/workspaces/{created['id']}", headers=OWNER)
        self.assertEqual(fetched.status_code, 200)
        audit = client.get(
            f"/observatory/workspaces/{created['id']}/audit", headers=OWNER)
        self.assertEqual(audit.status_code, 200)
        body = audit.json()
        self.assertIn("governance_state", body)
        self.assertIn("audit_chain", body)
        actions = [record["action"] for record in body["audit_chain"]]
        self.assertIn("workspace_created", actions)

    def test_private_hidden_from_others(self):
        client = _client(self)
        created = _create(client)
        missing = client.get(
            f"/observatory/workspaces/{created['id']}", headers=OTHER)
        self.assertEqual(missing.status_code, 403)
        listing = client.get("/observatory/workspaces", headers=OTHER)
        self.assertEqual(listing.json(), [])

    def test_shared_visible_to_shared(self):
        client = _client(self)
        created = _create(client, visibility="shared",
                          shared_with=["op-other"])
        response = client.get(
            f"/observatory/workspaces/{created['id']}", headers=OTHER)
        self.assertEqual(response.status_code, 200)

    def test_public_visible(self):
        client = _client(self)
        created = _create(client, visibility="public")
        response = client.get(
            f"/observatory/workspaces/{created['id']}", headers=OTHER)
        self.assertEqual(response.status_code, 200)

    def test_non_owner_cannot_update_or_delete(self):
        client = _client(self)
        created = _create(client, visibility="public")
        update = client.put(
            f"/observatory/workspaces/{created['id']}",
            json={"name": "Hijacked"}, headers=OTHER)
        self.assertEqual(update.status_code, 403)
        delete = client.delete(
            f"/observatory/workspaces/{created['id']}", headers=OTHER)
        self.assertEqual(delete.status_code, 403)

    def test_update_version_and_delete(self):
        client = _client(self)
        created = _create(client)
        updated = client.put(
            f"/observatory/workspaces/{created['id']}",
            json={"name": "Renamed"}, headers=OWNER)
        self.assertEqual(updated.json()["version"], 2)
        deleted = client.delete(
            f"/observatory/workspaces/{created['id']}", headers=OWNER)
        self.assertEqual(deleted.json()["status"], "deleted")
        missing = client.get(
            f"/observatory/workspaces/{created['id']}", headers=OWNER)
        self.assertEqual(missing.status_code, 404)

    def test_export_bundle_and_audit(self):
        client = _client(self)
        created = _create(client)
        exported = client.get(
            f"/observatory/workspaces/{created['id']}/export", headers=OWNER)
        self.assertEqual(exported.status_code, 200)
        body = exported.json()
        self.assertEqual(body["bundle_version"],
                         "observatory-workspace-export-v1")
        self.assertEqual(body["workspace"]["query"]["q"], "priority")
        audit = client.get(
            f"/observatory/workspaces/{created['id']}/audit", headers=OWNER)
        actions = [record["action"] for record in audit.json()["audit_chain"]]
        self.assertIn("workspace_exported", actions)

    def test_secret_payload_rejected(self):
        client = _client(self)
        response = client.post(
            "/observatory/workspaces",
            json=_payload(name="x", query={"q": "password = \"supersecret1\""}),
            headers=OWNER)
        self.assertEqual(response.status_code, 400)


class RolesLifecycle(unittest.TestCase):
    def _owned(self, client):
        return _create(client)

    def test_grant_revoke_flow(self):
        client = _client(self)
        created = self._owned(client)
        workspace_id = created["id"]
        granted = client.post(
            f"/observatory/workspaces/{workspace_id}/roles",
            json={"operator_id": "op-other", "role": "viewer"},
            headers=OWNER)
        self.assertEqual(granted.status_code, 200)
        self.assertEqual(granted.json()["role"], "viewer")
        visible = client.get(
            f"/observatory/workspaces/{workspace_id}", headers=OTHER)
        self.assertEqual(visible.status_code, 200)
        revoked = client.delete(
            f"/observatory/workspaces/{workspace_id}/roles/op-other",
            headers=OWNER)
        self.assertEqual(revoked.json()["status"], "revoked")
        hidden = client.get(
            f"/observatory/workspaces/{workspace_id}", headers=OTHER)
        self.assertEqual(hidden.status_code, 403)

    def test_grant_requires_permission(self):
        client = _client(self)
        created = self._owned(client)
        denied = client.post(
            f"/observatory/workspaces/{created['id']}/roles",
            json={"operator_id": "op-x", "role": "viewer"},
            headers=OTHER)
        self.assertEqual(denied.status_code, 403)

    def test_owner_role_protected(self):
        client = _client(self)
        created = self._owned(client)
        workspace_id = created["id"]
        reassign = client.post(
            f"/observatory/workspaces/{workspace_id}/roles",
            json={"operator_id": "op-owner", "role": "viewer"},
            headers=OWNER)
        self.assertEqual(reassign.status_code, 400)
        revoke = client.delete(
            f"/observatory/workspaces/{workspace_id}/roles/op-owner",
            headers=OWNER)
        self.assertEqual(revoke.status_code, 400)

    def test_snapshot_chain_links(self):
        client = _client(self)
        created = self._owned(client)
        workspace_id = created["id"]
        client.put(f"/observatory/workspaces/{workspace_id}",
                   json={"name": "V2"}, headers=OWNER)
        audit = client.get(
            f"/observatory/workspaces/{workspace_id}/audit", headers=OWNER)
        snapshots = audit.json()["snapshots"]
        self.assertEqual(len(snapshots), 2)
        by_type = {snapshot["snapshot_type"]: snapshot
                   for snapshot in snapshots}
        self.assertIsNone(by_type["created"]["previous_hash"])
        self.assertEqual(by_type["updated"]["previous_hash"],
                         by_type["created"]["snapshot_hash"])

    def test_audit_chain_links(self):
        client = _client(self)
        created = self._owned(client)
        workspace_id = created["id"]
        audit = client.get(
            f"/observatory/workspaces/{workspace_id}/audit", headers=OWNER)
        chain = audit.json()["audit_chain"]
        self.assertGreaterEqual(len(chain), 1)
        for previous, current in zip(
                sorted(chain, key=lambda record: record["timestamp"]),
                sorted(chain, key=lambda record: record["timestamp"])[1:]):
            self.assertEqual(current["previous_hash"], previous["audit_hash"])

    def test_contributor_can_update_not_delete(self):
        client = _client(self)
        created = self._owned(client)
        workspace_id = created["id"]
        client.post(f"/observatory/workspaces/{workspace_id}/roles",
                    json={"operator_id": "op-other", "role": "contributor"},
                    headers=OWNER)
        updated = client.put(
            f"/observatory/workspaces/{workspace_id}",
            json={"name": "By contributor"}, headers=OTHER)
        self.assertEqual(updated.status_code, 200)
        denied = client.delete(
            f"/observatory/workspaces/{workspace_id}", headers=OTHER)
        self.assertEqual(denied.status_code, 403)


if __name__ == "__main__":
    unittest.main()
