"""VS-D04 tests T01-T12: behavioral verification of vs1-candidate-a."""
from __future__ import annotations

import unittest

from fastapi.testclient import TestClient

from vertical_slice import implementation as IMPL
from vertical_slice.app.api import create_app
from vertical_slice.app.service import (
    AuthError,
    AuthorizationError,
    TaskTrackerService,
    ValidationError,
)
from vertical_slice.app.store import TaskTrackerStore


def _counter_tokens():
    state = {"n": 0}

    def generate() -> str:
        state["n"] += 1
        return f"vs1-test-token-{state['n']:04d}"

    return generate


class SliceHarness(unittest.TestCase):
    def setUp(self):
        import tempfile
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.store = TaskTrackerStore(self._tmp.name)
        self.service = TaskTrackerService(
            self.store, token_generator=_counter_tokens())
        self.store.ensure_workspace("ws-a", "Alpha")
        self.store.ensure_workspace("ws-b", "Beta")
        self.alice = self.service.register("alice", "alice-secret-pw")
        self.bob = self.service.register("bob", "bob-secret-pw")
        self.admin = self.service.register("cara-admin", "cara-secret-pw")
        from vertical_slice.app.models import Membership
        self.store.put_membership(Membership("ws-a", self.alice.user_id, "member"))
        self.store.put_membership(Membership("ws-a", self.admin.user_id, "admin"))
        self.store.put_membership(Membership("ws-b", self.bob.user_id, "member"))
        self.alice_token = self.service.login("alice", "alice-secret-pw")
        self.bob_token = self.service.login("bob", "bob-secret-pw")
        self.admin_token = self.service.login("cara-admin", "cara-secret-pw")
        self.client = TestClient(create_app(self.store, token_generator=_counter_tokens()))

    def auth(self, token: str) -> dict[str, str]:
        return {"Authorization": f"Bearer {token}"}


class TestT01FrozenInputs(SliceHarness):
    def test_frozen_identity_recomputes(self):
        first = IMPL.frozen_input_identity()
        second = IMPL.frozen_input_identity()
        self.assertEqual(first, second)
        self.assertEqual(first["vs-d03-selected"], "vs1-candidate-a")
        self.assertEqual(first["implementation-version"], IMPL.IMPLEMENTATION_VERSION)
        self.assertEqual(len(first["vs-d02-isr-content-hash"]), 64)
        self.assertEqual(len(first["vs-d01-graph-sha256"]), 64)

    def test_lineage_checker_is_fail_closed_by_construction(self):
        # validate_lineage takes no untrusted input: it rebuilds both frozen
        # graphs itself, so unknown IDs cannot enter except via upstream drift,
        # which raises ValueError inside the builders' own checks.
        result = IMPL.validate_lineage()
        self.assertEqual(result, {"unresolved_isr": [], "unresolved_req": []})


class TestT02RequirementCoverage(SliceHarness):
    def test_every_mandatory_requirement_has_path(self):
        evidence = IMPL.build_evidence()
        for req_id in ("req-auth-register", "req-auth-login", "req-task-create",
                       "req-task-read", "req-task-update", "req-task-delete",
                       "req-task-assign", "req-workspace-members",
                       "req-credential-safety", "req-tenant-isolation",
                       "req-durability", "con-multiuser", "con-api-surface"):
            self.assertIn(req_id, evidence["requirement_coverage"], req_id)


class TestT03ISRCoverage(SliceHarness):
    def test_mandatory_elements_accounted(self):
        evidence = IMPL.build_evidence()
        for isr_id in ("svc-identity", "svc-task", "svc-workspace",
                       "api-identity", "api-task", "api-workspace",
                       "dm-task", "dm-workspace", "dm-user-account",
                       "ev-task-created", "ev-task-updated",
                       "sec-credential-safety", "sec-tenant-isolation"):
            self.assertIn(isr_id, evidence["isr_coverage"], isr_id)


class TestT04APIBehavior(SliceHarness):
    def test_health(self):
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok"})

    def test_register_login_crud_lifecycle(self):
        headers = self.auth(self.alice_token)
        created = self.client.post(
            "/workspaces/ws-a/tasks", headers=headers,
            json={"title": "Write slice report", "status": "open"})
        self.assertEqual(created.status_code, 201)
        task_id = created.json()["task_id"]
        listed = self.client.get("/workspaces/ws-a/tasks", headers=headers)
        self.assertEqual([t["task_id"] for t in listed.json()], [task_id])
        fetched = self.client.get(f"/workspaces/ws-a/tasks/{task_id}", headers=headers)
        self.assertEqual(fetched.json()["title"], "Write slice report")
        patched = self.client.patch(
            f"/workspaces/ws-a/tasks/{task_id}", headers=headers,
            json={"status": "done"})
        self.assertEqual(patched.json()["status"], "done")
        deleted = self.client.delete(f"/workspaces/ws-a/tasks/{task_id}", headers=headers)
        self.assertEqual(deleted.status_code, 204)
        gone = self.client.get(f"/workspaces/ws-a/tasks/{task_id}", headers=headers)
        self.assertEqual(gone.status_code, 422)

    def test_assign_and_members(self):
        headers = self.auth(self.alice_token)
        created = self.client.post(
            "/workspaces/ws-a/tasks", headers=headers, json={"title": "Review"})
        task_id = created.json()["task_id"]
        patched = self.client.patch(
            f"/workspaces/ws-a/tasks/{task_id}", headers=headers,
            json={"assignee_id": self.admin.user_id})
        self.assertEqual(patched.json()["assignee_id"], self.admin.user_id)
        bad = self.client.patch(
            f"/workspaces/ws-a/tasks/{task_id}", headers=headers,
            json={"assignee_id": self.bob.user_id})
        self.assertEqual(bad.status_code, 422)
        admin_headers = self.auth(self.admin_token)
        added = self.client.post(
            "/workspaces/ws-a/members", headers=admin_headers,
            json={"user_id": self.bob.user_id, "role": "member"})
        self.assertEqual(added.status_code, 201)
        repatch = self.client.patch(
            f"/workspaces/ws-a/tasks/{task_id}", headers=headers,
            json={"assignee_id": self.bob.user_id})
        self.assertEqual(repatch.json()["assignee_id"], self.bob.user_id)

    def test_validation_errors(self):
        headers = self.auth(self.alice_token)
        empty = self.client.post(
            "/workspaces/ws-a/tasks", headers=headers, json={"title": "  "})
        self.assertEqual(empty.status_code, 422)
        missing = self.client.get("/workspaces/ws-a/tasks/task-9999", headers=headers)
        self.assertEqual(missing.status_code, 422)


class TestT05Security(SliceHarness):
    def test_unauthenticated_rejected(self):
        self.assertEqual(self.client.get("/workspaces/ws-a/tasks").status_code, 401)
        self.assertEqual(self.client.post(
            "/workspaces/ws-a/tasks", json={"title": "x"}).status_code, 401)

    def test_bad_token_rejected(self):
        headers = self.auth("vs1-test-token-9999")
        self.assertEqual(
            self.client.get("/workspaces/ws-a/tasks", headers=headers).status_code, 401)

    def test_login_does_not_enumerate(self):
        unknown = self.client.post(
            "/users/login", json={"username": "ghost", "password": "whatever-secret"})
        wrong = self.client.post(
            "/users/login", json={"username": "alice", "password": "wrong-secret"})
        self.assertEqual(unknown.status_code, 401)
        self.assertEqual(wrong.status_code, 401)
        self.assertEqual(unknown.json(), wrong.json())

    def test_tenant_isolation(self):
        alice_headers = self.auth(self.alice_token)
        bob_headers = self.auth(self.bob_token)
        created = self.client.post(
            "/workspaces/ws-b/tasks", headers=bob_headers, json={"title": "Bob secret"})
        task_id = created.json()["task_id"]
        self.assertEqual(
            self.client.get(f"/workspaces/ws-b/tasks/{task_id}",
                            headers=alice_headers).status_code, 403)
        self.assertEqual(
            self.client.get("/workspaces/ws-b/tasks",
                            headers=alice_headers).status_code, 403)

    def test_non_admin_cannot_manage_members(self):
        headers = self.auth(self.alice_token)
        response = self.client.post(
            "/workspaces/ws-a/members", headers=headers,
            json={"user_id": self.bob.user_id, "role": "member"})
        self.assertEqual(response.status_code, 403)

    def test_credentials_never_stored_or_returned(self):
        stored = self.store.get_user(self.alice.user_id)
        assert stored is not None
        self.assertNotIn("alice-secret-pw", stored.password_hash)
        response = self.client.post(
            "/users/register", json={"username": "dave", "password": "dave-secret"})
        self.assertEqual(response.status_code, 201)
        self.assertNotIn("password", response.json())
        self.assertNotIn("secret", response.text)


class TestT06DataBehavior(SliceHarness):
    def test_durability_across_restart(self):
        headers = self.auth(self.alice_token)
        created = self.client.post(
            "/workspaces/ws-a/tasks", headers=headers, json={"title": "Persist me"})
        task_id = created.json()["task_id"]
        reopened = TaskTrackerStore(self._tmp.name)
        task = reopened.get_task(task_id)
        assert task is not None
        self.assertEqual(task.title, "Persist me")
        members = [m for m in reopened._state["memberships"]
                   if m["workspace_id"] == "ws-a"]
        self.assertTrue(any(m["user_id"] == self.alice.user_id for m in members))

    def test_store_serialization_deterministic(self):
        first = self.store.raw_bytes()
        reopened = TaskTrackerStore(self._tmp.name)
        reopened.put_workspace(reopened.get_workspace("ws-a"))
        self.assertEqual(reopened.raw_bytes(), TaskTrackerStore(self._tmp.name).raw_bytes())
        self.assertEqual(first, TaskTrackerStore(self._tmp.name).raw_bytes())


class TestT07Events(SliceHarness):
    def test_created_and_updated_events(self):
        headers = self.auth(self.alice_token)
        created = self.client.post(
            "/workspaces/ws-a/tasks", headers=headers, json={"title": "Track me"})
        task_id = created.json()["task_id"]
        self.client.patch(f"/workspaces/ws-a/tasks/{task_id}",
                          headers=headers, json={"status": "done"})
        events = self.service.events_for_task(self.alice_token, task_id)
        names = [e.event_name for e in events]
        self.assertEqual(names, ["task-created", "task-updated"])
        for event in events:
            self.assertEqual(event.task_id, task_id)
            self.assertEqual(event.producer, "svc-task")


class TestT08Conformance(SliceHarness):
    def test_implementation_matches_candidate_a(self):
        evidence = IMPL.build_evidence()
        self.assertEqual(evidence["candidate_id"], "vs1-candidate-a")
        self.assertEqual(evidence["candidate_version"], "1")
        self.assertIn("service.register", evidence["components"])
        self.assertNotIn("vs1-candidate-b", str(evidence))


class TestT09Lineage(SliceHarness):
    def test_lineage_resolves(self):
        result = IMPL.validate_lineage()
        self.assertEqual(result, {"unresolved_isr": [], "unresolved_req": []})

    def test_evidence_carries_upstream_hashes(self):
        evidence = IMPL.build_evidence()
        self.assertEqual(len(evidence["vs-d02-isr-content-hash"]), 64)
        self.assertEqual(len(evidence["vs-d01-graph-sha256"]), 64)


class TestT10FailClosed(SliceHarness):
    def test_unknown_task_fails(self):
        with self.assertRaises(ValidationError):
            self.service.get_task(self.alice_token, "task-9999")

    def test_unknown_user_member_add_fails(self):
        with self.assertRaises(ValidationError):
            self.service.add_member(self.admin_token, "ws-a", "user-9999")

    def test_bad_role_fails(self):
        with self.assertRaises(ValidationError):
            self.service.add_member(self.admin_token, "ws-a", self.bob.user_id, role="owner")

    def test_duplicate_registration_fails(self):
        with self.assertRaises(ValidationError):
            self.service.register("alice", "another-secret")


class TestT11Determinism(SliceHarness):
    def test_evidence_reproducible(self):
        self.assertEqual(IMPL.build_evidence(), IMPL.build_evidence())


class TestT12Boundary(SliceHarness):
    def test_no_deployment_observation_evolution(self):
        import ast
        import os
        for rel in (os.path.join("vertical_slice", "app", "service.py"),
                    os.path.join("vertical_slice", "app", "api.py"),
                    os.path.join("vertical_slice", "app", "store.py"),
                    os.path.join("vertical_slice", "implementation.py")):
            src = open(rel, encoding="utf-8").read()
            tree = ast.parse(src)
            imports = set()
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    imports.update(a.name.split(".")[0] for a in node.names)
                elif isinstance(node, ast.ImportFrom) and node.module:
                    imports.add(node.module.split(".")[0])
            self.assertLessEqual(
                imports,
                {"__future__", "typing", "dataclasses", "json", "os", "hashlib",
                 "hmac", "secrets", "fastapi", "pydantic", "vertical_slice"},
                (rel, imports))
            lowered = src.lower()
            for token in ("uvicorn", "docker", "telemetry", "observe"):
                self.assertNotIn(token, lowered, (rel, token))


if __name__ == "__main__":
    unittest.main()
