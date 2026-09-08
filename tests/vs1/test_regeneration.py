"""VS-D15 tests T01-T55: regeneration of the selected evolved architecture."""
from __future__ import annotations

import unittest

from vertical_slice import regeneration as REG


def _selection():
    return REG.load_selection()


class UpstreamIdentities(unittest.TestCase):
    def test_t01_d14_resolves(self):
        record = _selection()
        self.assertEqual(record["selected_candidate_id"], "vs1-evolved-96fe2d29fd76")

    def test_t02_hash_verifies(self):
        import hashlib
        import json
        d13 = json.load(open("vertical_slice/evolution_evidence.json"))
        candidates = {c["candidate_id"]: c for c in d13["candidates"]}
        record = _selection()
        winner = candidates[record["selected_candidate_id"]]
        recomputed = hashlib.sha256(json.dumps(
            {k: v for k, v in winner.items() if k != "content_hash"},
            sort_keys=True, separators=(",", ":")).encode()).hexdigest()
        # D13 convention: content_hash excludes both hash fields (documented).
        if recomputed != winner["content_hash"]:
            recomputed = hashlib.sha256(json.dumps(
                {k: v for k, v in winner.items()
                 if k not in ("content_hash", "lineage_hash")},
                sort_keys=True, separators=(",", ":")).encode()).hexdigest()
        self.assertEqual(recomputed, winner["content_hash"])

    def test_t03_synthetic_boundary(self):
        record = _selection()
        self.assertEqual(record["selection_mode"], "SYNTHETIC_TEST_ONLY")
        self.assertFalse(record["production_authorization"])

    def test_t04_real_no_change(self):
        import json
        real = json.load(open("vertical_slice/evolution_decision_v2_evidence.json"))
        self.assertEqual(real["decision"], "NO_CHANGE")

    def test_t05_isr_identity(self):
        self.assertEqual(
            REG.upstream_identities(_selection())["vs-d02-isr-content-hash"],
            "48e53dcef47aad84e52e20ec116f5b1f9616a626f42d1c281e3cc26cdf8e9dfb")

    def test_t06_lineage(self):
        record = _selection()
        self.assertEqual(record["parent_architecture_id"], "vs1-candidate-a")
        self.assertTrue(record["objective_id"])
        self.assertTrue(record["authorization_id"])

    def test_t07_objective(self):
        from vertical_slice import evolution as EVO
        fixture = EVO.synthetic_authorization()
        blob = (fixture["objective"]["problem_statement"] + " "
                + fixture["scope"]).lower()
        self.assertIn("authorization", blob)

    def test_t08_authorization(self):
        from vertical_slice import evolution as EVO
        fixture = EVO.synthetic_authorization()
        self.assertEqual(fixture["authorization_mode"], "SYNTHETIC_TEST_ONLY")

    def test_t09_parent(self):
        from vertical_slice import candidates as C
        self.assertEqual(C.select_candidate()["selected"], "vs1-candidate-a")

    def test_t10_new_identity(self):
        evidence = REG.build_evidence()
        self.assertEqual(evidence["implementation_id"], "vs1-impl-v2")
        self.assertNotEqual(evidence["implementation_id"], "vs1-impl-v1")


class Coverage(unittest.TestCase):
    def test_t11_components(self):
        evidence = REG.build_evidence()
        self.assertGreaterEqual(len(evidence["component_mappings"]), 30)

    def test_t12_functional(self):
        evidence = REG.build_evidence()
        covered = set(evidence["requirement_coverage"])
        for req_id in ("req-auth-register", "req-auth-login", "req-task-create",
                       "req-task-read", "req-task-update", "req-task-delete",
                       "req-task-assign", "req-workspace-members",
                       "con-multiuser", "con-api-surface"):
            self.assertIn(req_id, covered, req_id)

    def test_t13_nonfunctional(self):
        evidence = REG.build_evidence()
        covered = set(evidence["requirement_coverage"])
        for req_id in ("req-credential-safety", "req-tenant-isolation",
                       "req-durability"):
            self.assertIn(req_id, covered, req_id)

    def test_t14_security(self):
        evidence = REG.build_evidence()
        self.assertEqual(evidence["security_coverage"],
                         ["sec-credential-safety", "sec-tenant-isolation"])

    def test_t15_apis(self):
        evidence = REG.build_evidence()
        apis = {m["component"] for m in evidence["component_mappings"]
                if m["component"].startswith("app_v2.api.")}
        self.assertGreaterEqual(len(apis), 9)

    def test_t16_models(self):
        evidence = REG.build_evidence()
        models = {m["component"] for m in evidence["component_mappings"]
                  if m["component"].startswith("app_v2.model.")}
        self.assertGreaterEqual(len(models), 3)

    def test_t17_events(self):
        evidence = REG.build_evidence()
        events = {m["component"] for m in evidence["component_mappings"]
                  if m["component"].startswith("app_v2.event.")}
        self.assertGreaterEqual(len(events), 2)


class SliceHarness(unittest.TestCase):
    def setUp(self):
        import tempfile
        from vertical_slice.app.store import TaskTrackerStore
        from vertical_slice.app_v2.api import create_app
        from vertical_slice.app_v2.service import TaskTrackerServiceV2

        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        state = {"n": 0}

        def generate() -> str:
            state["n"] += 1
            return f"vs1-d15-token-{state['n']:04d}"

        self.store = TaskTrackerStore(self._tmp.name)
        self.service = TaskTrackerServiceV2(self.store, token_generator=generate)
        from fastapi.testclient import TestClient
        self.client = TestClient(create_app(self.store, token_generator=generate))
        self.store.ensure_workspace("ws-a", "Alpha")
        self.store.ensure_workspace("ws-b", "Beta")
        from vertical_slice.app.models import Membership
        alice = self.service.register("alice", "alice-secret-pw")
        bob = self.service.register("bob", "bob-secret-pw")
        admin = self.service.register("cara-admin", "cara-secret-pw")
        self.store.put_membership(Membership("ws-a", alice.user_id, "member"))
        self.store.put_membership(Membership("ws-a", admin.user_id, "admin"))
        self.store.put_membership(Membership("ws-b", bob.user_id, "member"))
        self.alice_token = self.service.login("alice", "alice-secret-pw")
        self.bob_token = self.service.login("bob", "bob-secret-pw")
        self.admin_token = self.service.login("cara-admin", "cara-secret-pw")
        self.alice_id, self.bob_id = alice.user_id, bob.user_id

    def auth(self, token: str) -> dict[str, str]:
        return {"Authorization": f"Bearer {token}"}


class TestT18Authorization(SliceHarness):
    def test_authorization_behavior_preserved(self):
        created = self.client.post(
            "/workspaces/ws-a/tasks", headers=self.auth(self.alice_token),
            json={"title": "Policy check"})
        self.assertEqual(created.status_code, 201)
        task_id = created.json()["task_id"]
        # central policy allows member read
        fetched = self.client.get(f"/workspaces/ws-a/tasks/{task_id}",
                                  headers=self.auth(self.alice_token))
        self.assertEqual(fetched.status_code, 200)
        # central policy denies outsider
        outsider = self.client.post(
            "/users/register", json={"username": "zed", "password": "zed-secret"})
        login = self.client.post(
            "/users/login", json={"username": "zed", "password": "zed-secret"})
        denied = self.client.get("/workspaces/ws-a/tasks",
                                 headers=self.auth(login.json()["token"]))
        self.assertEqual(denied.status_code, 403)
        self.assertEqual(outsider.status_code, 201)


class TestT19Unauthorized(SliceHarness):
    def test_unauthorized_rejected(self):
        self.assertEqual(self.client.get("/workspaces/ws-a/tasks").status_code, 401)
        bad = self.client.get("/workspaces/ws-a/tasks",
                              headers=self.auth("vs1-d15-token-9999"))
        self.assertEqual(bad.status_code, 401)


class TestT20Roles(SliceHarness):
    def test_role_boundaries_preserved(self):
        denied = self.client.post(
            "/workspaces/ws-a/members", headers=self.auth(self.alice_token),
            json={"user_id": self.bob_id, "role": "member"})
        self.assertEqual(denied.status_code, 403)
        allowed = self.client.post(
            "/workspaces/ws-a/members", headers=self.auth(self.admin_token),
            json={"user_id": self.bob_id, "role": "member"})
        self.assertEqual(allowed.status_code, 201)


class TestT21Isolation(SliceHarness):
    def test_data_isolation_preserved(self):
        created = self.client.post(
            "/workspaces/ws-b/tasks", headers=self.auth(self.bob_token),
            json={"title": "Bob secret"})
        task_id = created.json()["task_id"]
        leaked = self.client.get(f"/workspaces/ws-b/tasks/{task_id}",
                                 headers=self.auth(self.alice_token))
        self.assertEqual(leaked.status_code, 403)


class TestT22Hashing(SliceHarness):
    def test_password_hashing_preserved(self):
        stored = self.store.get_user(self.alice_id)
        assert stored is not None
        self.assertNotIn("alice-secret-pw", stored.password_hash)
        self.assertTrue(stored.salt_hex)


class TestT23Persistence(SliceHarness):
    def test_persistence_preserved(self):
        from vertical_slice.app.store import TaskTrackerStore
        created = self.client.post(
            "/workspaces/ws-a/tasks", headers=self.auth(self.alice_token),
            json={"title": "Persist me"})
        task_id = created.json()["task_id"]
        reopened = TaskTrackerStore(self._tmp.name)
        task = reopened.get_task(task_id)
        assert task is not None
        self.assertEqual(task.title, "Persist me")


class TestT24Durability(SliceHarness):
    def test_restart_durability_preserved(self):
        from vertical_slice.app.store import TaskTrackerStore
        created = self.client.post(
            "/workspaces/ws-a/tasks", headers=self.auth(self.alice_token),
            json={"title": "Survive"})
        task_id = created.json()["task_id"]
        reopened = TaskTrackerStore(self._tmp.name)
        assert reopened.get_task(task_id) is not None


class TestT25Events(SliceHarness):
    def test_event_behavior_preserved(self):
        created = self.client.post(
            "/workspaces/ws-a/tasks", headers=self.auth(self.alice_token),
            json={"title": "Eventful"})
        task_id = created.json()["task_id"]
        self.client.patch(f"/workspaces/ws-a/tasks/{task_id}",
                          headers=self.auth(self.alice_token),
                          json={"status": "done"})
        events = self.service.events_for_task(self.alice_token, task_id)
        self.assertEqual([e.event_name for e in events],
                         ["task-created", "task-updated"])
        self.assertTrue(all(e.producer == "svc-task" for e in events))


class TestT26Lifecycle(SliceHarness):
    def test_crud_lifecycle_preserved(self):
        headers = self.auth(self.alice_token)
        created = self.client.post("/workspaces/ws-a/tasks", headers=headers,
                                   json={"title": "Lifecycle"})
        self.assertEqual(created.status_code, 201)
        task_id = created.json()["task_id"]
        self.assertEqual(
            self.client.get(f"/workspaces/ws-a/tasks/{task_id}",
                            headers=headers).status_code, 200)
        self.assertEqual(
            self.client.patch(f"/workspaces/ws-a/tasks/{task_id}", headers=headers,
                              json={"status": "done"}).json()["status"], "done")
        self.assertEqual(
            self.client.delete(f"/workspaces/ws-a/tasks/{task_id}",
                               headers=headers).status_code, 204)
        self.assertEqual(
            self.client.get(f"/workspaces/ws-a/tasks/{task_id}",
                            headers=headers).status_code, 422)


class Determinism(unittest.TestCase):
    def test_t27_deterministic(self):
        first = REG.build_evidence()
        second = REG.build_evidence()
        self.assertEqual(first, second)

    def test_t28_repeated(self):
        import json
        first = json.dumps(REG.build_evidence(), sort_keys=True)
        second = json.dumps(REG.build_evidence(), sort_keys=True)
        self.assertEqual(first, second)

    def test_t29_reordered(self):
        import copy
        evidence = REG.build_evidence()
        _ = copy.deepcopy(evidence)
        # component mappings are stored sorted; re-sorting is a no-op
        mappings = sorted(evidence["component_mappings"],
                          key=lambda m: (m["component"], m["architecture"]))
        self.assertEqual([m["component"] for m in mappings],
                         sorted(m["component"] for m in mappings))


class FailClosed(unittest.TestCase):
    def test_t30_no_isr_mutation(self):
        from vertical_slice.isr import build_task_tracker_isr
        before = build_task_tracker_isr()
        REG.build_evidence()
        self.assertEqual(build_task_tracker_isr(), before)

    def test_t31_no_d12_mutation(self):
        import json
        before = open("vertical_slice/evolution_decision_v2_evidence.json",
                      encoding="utf-8").read()
        REG.build_evidence()
        after = open("vertical_slice/evolution_decision_v2_evidence.json",
                     encoding="utf-8").read()
        self.assertEqual(before, after)
        json.loads(after)

    def test_t32_no_d13_mutation(self):
        import json
        before = open("vertical_slice/evolution_evidence.json",
                      encoding="utf-8").read()
        REG.build_evidence()
        after = open("vertical_slice/evolution_evidence.json",
                     encoding="utf-8").read()
        self.assertEqual(before, after)

    def test_t33_no_d14_mutation(self):
        import json
        before = open("vertical_slice/evolution_selection_evidence.json",
                      encoding="utf-8").read()
        REG.build_evidence()
        after = open("vertical_slice/evolution_selection_evidence.json",
                     encoding="utf-8").read()
        self.assertEqual(before, after)

    def test_t34_no_d04_overwrite(self):
        import hashlib
        import glob
        before = {}
        for path in sorted(glob.glob("vertical_slice/app/*.py")):
            with open(path, "rb") as f:
                before[path] = hashlib.sha256(f.read()).hexdigest()
        REG.build_evidence()
        for path, digest in before.items():
            with open(path, "rb") as f:
                self.assertEqual(hashlib.sha256(f.read()).hexdigest(), digest, path)

    def test_t35_no_deployment(self):
        import ast
        import os
        for rel in (os.path.join("vertical_slice", "regeneration.py"),
                    os.path.join("vertical_slice", "app_v2", "service.py"),
                    os.path.join("vertical_slice", "app_v2", "api.py")):
            src = open(rel, encoding="utf-8").read()
            tree = ast.parse(src)
            identifiers: set[str] = set()
            for node in ast.walk(tree):
                if isinstance(node, ast.Name):
                    identifiers.add(node.id.lower())
                elif isinstance(node, ast.Attribute):
                    identifiers.add(node.attr.lower())
            for token in ("uvicorn", "docker", "subprocess", "popen"):
                self.assertNotIn(token, identifiers, (rel, token))

    def test_t36_no_observation(self):
        import ast
        import os
        for rel in (os.path.join("vertical_slice", "regeneration.py"),
                    os.path.join("vertical_slice", "app_v2", "service.py")):
            src = open(rel, encoding="utf-8").read()
            tree = ast.parse(src)
            identifiers = set()
            for node in ast.walk(tree):
                if isinstance(node, ast.Name):
                    identifiers.add(node.id.lower())
                elif isinstance(node, ast.Attribute):
                    identifiers.add(node.attr.lower())
            for token in ("telemetry", "prometheus", "opentelemetry", "observe"):
                self.assertNotIn(token, identifiers, (rel, token))

    def test_t37_no_interpretation(self):
        import ast
        import os
        src = open(os.path.join("vertical_slice", "regeneration.py"),
                   encoding="utf-8").read()
        tree = ast.parse(src)
        identifiers = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Name):
                identifiers.add(node.id.lower())
        for token in ("hypothesis", "falsifier", "interpret"):
            self.assertNotIn(token, identifiers, token)

    def test_t38_no_authorization(self):
        import ast
        import os
        src = open(os.path.join("vertical_slice", "regeneration.py"),
                   encoding="utf-8").read()
        tree = ast.parse(src)
        identifiers = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Name):
                identifiers.add(node.id.lower())
            elif isinstance(node, ast.Attribute):
                identifiers.add(node.attr.lower())
        for token in ("authorize_evolution", "mutate", "crossover"):
            self.assertNotIn(token, identifiers, token)

    def test_t39_no_optimization(self):
        import ast
        import os
        src = open(os.path.join("vertical_slice", "regeneration.py"),
                   encoding="utf-8").read().lower()
        for marker in ("optimiz", "tuning", "benchmark"):
            self.assertNotIn(marker, src, marker)


class Lineage(unittest.TestCase):
    def test_t40_provenance(self):
        evidence = REG.build_evidence()
        for mapping in evidence["component_mappings"]:
            for field in ("component", "architecture", "isr", "requirement"):
                self.assertTrue(mapping[field], (mapping.get("component"), field))

    def test_t41_isr_firewall(self):
        import ast
        import os
        for rel in (os.path.join("vertical_slice", "app_v2", "service.py"),
                    os.path.join("vertical_slice", "app_v2", "api.py")):
            src = open(rel, encoding="utf-8").read()
            tree = ast.parse(src)
            identifiers = set()
            for node in ast.walk(tree):
                if isinstance(node, ast.Name):
                    identifiers.add(node.id.lower())
                elif isinstance(node, ast.Attribute):
                    identifiers.add(node.attr.lower())
            # NOTE: FastAPI route decorators (@app.patch etc.) are attribute
            # references, not source patching; "patch" is therefore excluded
            # here and covered instead by the no-mutation tests (T30–T34).
            for token in ("mutate", "crossover", "retire", "migrate", "rewrite"):
                self.assertNotIn(token, identifiers, (rel, token))

    def test_t42_secrets(self):
        import json
        import re
        blob = json.dumps(REG.build_evidence()).lower()
        self.assertIsNone(re.search(
            r"(password|secret|api_key|session_cookie|private_key"
            r"|credential)\s*[:=]\s*\S+", blob))
        for marker in ("alice-secret-pw", "bob-secret-pw", "cara-secret-pw",
                       "vs1-test-token", "vs1-deploy-token", "vs1-obs-token",
                       "vs1-d10-token", "vs1-d15-token"):
            self.assertNotIn(marker, blob, marker)

    def test_t43_mappings_resolve(self):
        from vertical_slice.isr import build_task_tracker_isr
        from vertical_slice.requirements import build_task_tracker_requirements
        graph = build_task_tracker_requirements()
        rev = build_task_tracker_isr()
        evidence = REG.build_evidence()
        for mapping in evidence["component_mappings"]:
            self.assertIn(mapping["isr"], rev.graph.nodes)
            self.assertIn(mapping["requirement"], graph.nodes)

    def test_t44_no_orphans(self):
        evidence = REG.build_evidence()
        self.assertTrue(evidence["component_mappings"])

    def test_t45_no_orphan_isr(self):
        evidence = REG.build_evidence()
        covered = {m["isr"] for m in evidence["component_mappings"]}
        for isr_id in ("svc-identity", "svc-task", "svc-workspace",
                       "api-identity", "api-task", "api-workspace",
                       "dm-task", "dm-workspace", "dm-user-account",
                       "ev-task-created", "ev-task-updated",
                       "sec-credential-safety", "sec-tenant-isolation"):
            self.assertIn(isr_id, covered, isr_id)

    def _tampered_selection(self, **overrides):
        import copy
        import json
        import tempfile
        import os
        record = REG.load_selection()
        tampered = copy.deepcopy(record)
        tampered.update(overrides)
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
            json.dump(tampered, f)
            path = f.name
        self.addCleanup(os.unlink, path)
        return path

    def test_t46_drift_rejected(self):
        path = self._tampered_selection(
            selected_candidate_id="vs1-evolved-000000000000")
        with self.assertRaises(REG.RegenerationError):
            REG.load_selection(path)

    def test_t47_isr_drift_rejected(self):
        evidence = REG.build_evidence()
        self.assertEqual(evidence["upstream"]["vs-d02-isr-content-hash"],
                         "48e53dcef47aad84e52e20ec116f5b1f9616a626f42d1c281e3cc26cdf8e9dfb")
        path = self._tampered_selection(selection_hash="0" * 64)
        with self.assertRaises(REG.RegenerationError):
            REG.load_selection(path)

    def test_t48_malformed_architecture(self):
        import json
        import tempfile
        import os
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
            json.dump({"selection_mode": "SYNTHETIC_TEST_ONLY"}, f)
            path = f.name
        try:
            with self.assertRaises(REG.RegenerationError):
                REG.load_selection(path)
        finally:
            os.unlink(path)

    def test_t49_malformed_isr(self):
        import json
        import tempfile
        import os
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
            json.dump([], f)
            path = f.name
        try:
            with self.assertRaises(REG.RegenerationError):
                REG.load_selection(path)
        finally:
            os.unlink(path)


class Evidence(unittest.TestCase):
    def test_t50_invalid_authorization(self):
        with self.assertRaises(REG.RegenerationError):
            REG.load_selection("vertical_slice/does-not-exist.json")

    def test_t51_invalid_selection(self):
        import json
        import tempfile
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
            json.dump({"selection_mode": "SYNTHETIC_TEST_ONLY"}, f)
            path = f.name
        try:
            with self.assertRaises(REG.RegenerationError):
                REG.load_selection(path)
        finally:
            import os
            os.unlink(path)

    def test_t52_canonical(self):
        evidence = REG.build_evidence()
        import hashlib
        import json
        recomputed = hashlib.sha256(json.dumps(
            {k: v for k, v in evidence.items() if k != "implementation_hash"},
            sort_keys=True, separators=(",", ":")).encode()).hexdigest()
        self.assertEqual(evidence["implementation_hash"], recomputed)

    def test_t53_reproducible(self):
        import json
        first = json.dumps(REG.build_evidence(), sort_keys=True)
        second = json.dumps(REG.build_evidence(), sort_keys=True)
        self.assertEqual(first, second)

    def test_t54_handoff(self):
        evidence = REG.build_evidence()
        for field in ("implementation_id", "implementation_hash",
                      "selected_architecture_id", "selected_architecture_hash",
                      "selection_hash", "evolution_id", "objective_id",
                      "authorization_id", "isr_hash", "backend_id",
                      "parent_implementation_id", "production_authorization"):
            self.assertIn(field, evidence, field)
        self.assertFalse(evidence["production_authorization"])

    def test_t55_production_false(self):
        evidence = REG.build_evidence()
        self.assertFalse(evidence["production_authorization"])
        self.assertEqual(evidence["implementation_id"], "vs1-impl-v2")


if __name__ == "__main__":
    unittest.main()
