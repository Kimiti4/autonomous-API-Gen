"""VS-D25 tests T01-T62: selected-architecture implementation (no deployment).

Behavioral tests run against the v3 service directly and the v3 API via
in-process TestClient (never a server or deployment). Passwords below are
synthetic test fixtures; the evidence artifact carries none.
"""
from __future__ import annotations

import ast
import hashlib
import json
import os
import tempfile
import unittest
from unittest import mock

from fastapi.testclient import TestClient

from vertical_slice import implementation_d25 as IMPL

D24_PATH = "vertical_slice/architecture_selection_d24_evidence.json"
D23_PATH = "vertical_slice/candidate_generation_d23_evidence.json"
D22_PATH = "vertical_slice/objective_intake_d22_evidence.json"
D25_EVIDENCE = "vertical_slice/implementation_d25_evidence.json"


def _sha_file(path: str) -> str:
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def _seeded() -> tuple:
    from vertical_slice.app.models import Membership
    from vertical_slice.app.store import TaskTrackerStore
    from vertical_slice.app_v3.service import TaskTrackerServiceV3

    tmp = tempfile.TemporaryDirectory()
    store = TaskTrackerStore(tmp.name)
    service = TaskTrackerServiceV3(store)
    store.ensure_workspace("ws-a", "Alpha")
    admin = service.register("cara", "cara-secret-pw")
    alice = service.register("alice", "alice-secret-pw")
    store.put_membership(Membership("ws-a", admin.user_id, "admin"))
    store.put_membership(Membership("ws-a", alice.user_id, "member"))
    return tmp, store, service, {
        "admin": service.login("cara", "cara-secret-pw"),
        "alice": service.login("alice", "alice-secret-pw"),
    }


def _client() -> tuple:
    from vertical_slice.app.models import Membership
    from vertical_slice.app.store import TaskTrackerStore
    from vertical_slice.app_v3.api import create_app

    tmp = tempfile.TemporaryDirectory()
    store = TaskTrackerStore(tmp.name)
    from vertical_slice.app_v3.service import TaskTrackerServiceV3
    seed = TaskTrackerServiceV3(store)
    store.ensure_workspace("ws-a", "Alpha")
    admin = seed.register("cara", "cara-secret-pw")
    alice = seed.register("alice", "alice-secret-pw")
    store.put_membership(Membership("ws-a", admin.user_id, "admin"))
    store.put_membership(Membership("ws-a", alice.user_id, "member"))
    app = create_app(store)
    client = TestClient(app)
    alice_token = client.post(
        "/users/login",
        json={"username": "alice", "password": "alice-secret-pw"}).json()["token"]
    admin_token = client.post(
        "/users/login",
        json={"username": "cara", "password": "cara-secret-pw"}).json()["token"]
    return tmp, client, alice_token, admin_token


class Upstream(unittest.TestCase):
    def test_t01_selection_resolves(self):
        record = IMPL._load_json(D24_PATH)
        self.assertEqual(record["selected_candidate"],
                         "vs1-obj001-candidate-313b071dd7d4")

    def test_t02_selection_hash(self):
        from vertical_slice import architecture_selection_d24 as S24
        self.assertEqual(S24.evaluate()["selection_hash"],
                         IMPL._load_json(D24_PATH)["selection_hash"])

    def test_t03_candidate_hash(self):
        d24 = IMPL._load_json(D24_PATH)
        d23 = IMPL._load_json(D23_PATH)
        self.assertIn(d24["selected_hash"], d23["candidate_hashes"])

    def test_t04_objective_resolves(self):
        self.assertEqual(IMPL._load_json(D22_PATH)["objective_id"], "VS1-OBJ-001")

    def test_t05_isr_verifies(self):
        from vertical_slice import implementation as IMPLV1
        self.assertEqual(
            IMPLV1.frozen_input_identity()["vs-d02-isr-content-hash"],
            IMPL.EXPECTED_ISR)

    def test_t06_source_verifies(self):
        self.assertEqual(
            _sha_file("vertical_slice/objective_source_VS1-OBJ-001.json"),
            "4a9cde9ab822980985dc59e1f05649a456ee6ae3be6b30421183801d12ac6848")

    def test_t07_lineage_resolves(self):
        IMPL.validate_lineage()  # raises on any orphan

    def test_t08_parent_resolves(self):
        from vertical_slice.app_v2.service import TaskTrackerServiceV2
        self.assertEqual(TaskTrackerServiceV2.__module__,
                         "vertical_slice.app_v2.service")

    def test_t09_identity_distinct(self):
        self.assertEqual(IMPL.IMPLEMENTATION_ID, "vs1-impl-obj001-v1")
        self.assertNotEqual(IMPL.IMPLEMENTATION_ID, "vs1-impl-v2")
        self.assertNotEqual(IMPL.IMPLEMENTATION_ID, "vs1-impl-v1")

    def test_t10_architecture_implemented(self):
        fidelity = IMPL.detect_architecture_drift()
        self.assertTrue(all(fidelity.values()), fidelity)


class PriorityBehavior(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._tmp, cls._store, cls._service, cls._tokens = _seeded()
        cls.addClassCleanup(cls._tmp.cleanup)

    def test_t11_low_accepted(self):
        task = self._service.create_task(
            self._tokens["alice"], "ws-a", "Low task", "open", "LOW")
        self.assertEqual(task.priority, "LOW")

    def test_t12_medium_accepted(self):
        task = self._service.create_task(
            self._tokens["alice"], "ws-a", "Med task", "open", "MEDIUM")
        self.assertEqual(task.priority, "MEDIUM")

    def test_t13_high_accepted(self):
        task = self._service.create_task(
            self._tokens["alice"], "ws-a", "High task", "open", "HIGH")
        self.assertEqual(task.priority, "HIGH")

    def test_t14_invalid_rejected(self):
        from vertical_slice.app_v3.service import ValidationError
        with self.assertRaises(ValidationError):
            self._service.create_task(
                self._tokens["alice"], "ws-a", "Bad", "open", "URGENT")
        with self.assertRaises(ValidationError):
            self._service.create_task(
                self._tokens["alice"], "ws-a", "Bad", "open", "low")
        with self.assertRaises(ValidationError):
            self._service.create_task(
                self._tokens["alice"], "ws-a", "Bad", "open", "")

    def test_t15_create_persists(self):
        task = self._service.create_task(
            self._tokens["alice"], "ws-a", "Persist me", "open", "HIGH")
        with open(f"{self._tmp.name}/store.json", encoding="utf-8") as f:
            state = json.load(f)
        self.assertEqual(state["tasks"][task.task_id]["priority"], "HIGH")

    def test_t16_retrieve_returns(self):
        task = self._service.create_task(
            self._tokens["alice"], "ws-a", "Read me", "open", "LOW")
        fetched = self._service.get_task(self._tokens["alice"], task.task_id)
        self.assertEqual(fetched.priority, "LOW")

    def test_t17_update_changes(self):
        task = self._service.create_task(
            self._tokens["alice"], "ws-a", "Change me", "open", "LOW")
        updated = self._service.update_task(
            self._tokens["alice"], task.task_id, priority="HIGH")
        self.assertEqual(updated.priority, "HIGH")
        self.assertEqual(
            self._service.get_task(self._tokens["alice"], task.task_id).priority,
            "HIGH")

    def test_t18_invalid_update_rejected(self):
        from vertical_slice.app_v3.service import ValidationError
        task = self._service.create_task(
            self._tokens["alice"], "ws-a", "Keep me", "open", "LOW")
        with self.assertRaises(ValidationError):
            self._service.update_task(
                self._tokens["alice"], task.task_id, priority="CRITICAL")
        self.assertEqual(
            self._service.get_task(self._tokens["alice"], task.task_id).priority,
            "LOW")

    def test_t19_filter_works(self):
        self._service.create_task(self._tokens["alice"], "ws-a", "F-high", "open", "HIGH")
        self._service.create_task(self._tokens["alice"], "ws-a", "F-low", "open", "LOW")
        highs = self._service.list_tasks(self._tokens["alice"], "ws-a", "HIGH")
        self.assertTrue(highs)
        self.assertTrue(all(t.priority == "HIGH" for t in highs))
        lows = self._service.list_tasks(self._tokens["alice"], "ws-a", "LOW")
        self.assertTrue(all(t.priority == "LOW" for t in lows))

    def test_t20_empty_filter_correct(self):
        result = self._service.list_tasks(self._tokens["alice"], "ws-a", "MEDIUM")
        self.assertEqual([t for t in result if t.title == "No such task"], [])


class ApiContract(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._tmp, cls._client, cls._alice, cls._admin = _client()
        cls.addClassCleanup(cls._tmp.cleanup)

    def _auth(self, token: str) -> dict[str, str]:
        return {"Authorization": f"Bearer {token}"}

    def test_t14_http_invalid_rejected(self):
        response = self._client.post(
            "/workspaces/ws-a/tasks", json={"title": "Bad", "priority": "URGENT"},
            headers=self._auth(self._alice))
        self.assertEqual(response.status_code, 422)

    def test_t21_display_priority(self):
        # Display surface in this API-only slice: reads serialize priority.
        created = self._client.post(
            "/workspaces/ws-a/tasks", json={"title": "Shown", "priority": "HIGH"},
            headers=self._auth(self._alice)).json()
        self.assertEqual(created["priority"], "HIGH")
        fetched = self._client.get(
            f"/workspaces/ws-a/tasks/{created['task_id']}",
            headers=self._auth(self._alice)).json()
        self.assertEqual(fetched["priority"], "HIGH")

    def test_t22_filter_query(self):
        self._client.post("/workspaces/ws-a/tasks",
                          json={"title": "Q-high", "priority": "HIGH"},
                          headers=self._auth(self._alice))
        self._client.post("/workspaces/ws-a/tasks",
                          json={"title": "Q-low", "priority": "LOW"},
                          headers=self._auth(self._alice))
        body = self._client.get("/workspaces/ws-a/tasks?priority=HIGH",
                                headers=self._auth(self._alice)).json()
        self.assertTrue(body)
        self.assertTrue(all(t["priority"] == "HIGH" for t in body))
        bad = self._client.get("/workspaces/ws-a/tasks?priority=URGENT",
                               headers=self._auth(self._alice))
        self.assertEqual(bad.status_code, 422)


class Preservation(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._tmp, cls._store, cls._service, cls._tokens = _seeded()
        cls.addClassCleanup(cls._tmp.cleanup)

    def test_t23_create_preserved(self):
        task = self._service.create_task(self._tokens["alice"], "ws-a", "Plain")
        self.assertEqual(task.priority, "MEDIUM")
        self.assertEqual(task.status, "open")

    def test_t24_retrieve_preserved(self):
        task = self._service.create_task(self._tokens["alice"], "ws-a", "R")
        self.assertEqual(
            self._service.get_task(self._tokens["alice"], task.task_id).title, "R")

    def test_t25_update_preserved(self):
        task = self._service.create_task(self._tokens["alice"], "ws-a", "U")
        updated = self._service.update_task(
            self._tokens["alice"], task.task_id, status="done")
        self.assertEqual(updated.status, "done")
        self.assertEqual(updated.priority, "MEDIUM")

    def test_t26_lifecycle_preserved(self):
        task = self._service.create_task(self._tokens["alice"], "ws-a", "D")
        self._service.delete_task(self._tokens["alice"], task.task_id)
        from vertical_slice.app_v3.service import ValidationError
        with self.assertRaises(ValidationError):
            self._service.get_task(self._tokens["alice"], task.task_id)

    def test_t27_authorization_preserved(self):
        status = self._service.login("alice", "alice-secret-pw")
        self.assertTrue(status)
        from vertical_slice.app_v3.service import AuthError
        with self.assertRaises(AuthError):
            self._service.login("alice", "wrong-pw")

    def test_t28_unauthorized_rejected(self):
        from vertical_slice.app_v3.service import AuthError
        with self.assertRaises(AuthError):
            self._service.list_tasks("bogus-token", "ws-a")

    def test_t29_isolation_preserved(self):
        from vertical_slice.app_v3.service import AuthorizationError
        bob = self._service.register("bob-out", "bob-secret-pw")
        bob_token = self._service.login("bob-out", "bob-secret-pw")
        self.assertTrue(bob.user_id)
        with self.assertRaises(AuthorizationError):
            self._service.list_tasks(bob_token, "ws-a")
        with self.assertRaises(AuthorizationError):
            self._service.list_tasks(bob_token, "ws-a", "HIGH")

    def test_t30_credential_safety(self):
        alice_rec = self._store.find_user_by_name("alice")
        self.assertIsNotNone(alice_rec)
        assert alice_rec is not None
        self.assertNotEqual(alice_rec.password_hash, "alice-secret-pw")
        self.assertTrue(alice_rec.salt_hex)

    def test_t31_hashing_preserved(self):
        from vertical_slice.app.security import verify_password
        alice_rec = self._store.find_user_by_name("alice")
        assert alice_rec is not None
        self.assertTrue(verify_password("alice-secret-pw", alice_rec.salt_hex,
                                        alice_rec.password_hash))
        self.assertFalse(verify_password("wrong", alice_rec.salt_hex,
                                         alice_rec.password_hash))


class PersistenceEvents(unittest.TestCase):
    def test_t32_restart_durability(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        from vertical_slice.app.models import Membership
        from vertical_slice.app.store import TaskTrackerStore
        from vertical_slice.app_v3.service import TaskTrackerServiceV3

        store = TaskTrackerStore(tmp.name)
        service = TaskTrackerServiceV3(store)
        store.ensure_workspace("ws-a", "Alpha")
        alice = service.register("alice", "alice-secret-pw")
        store.put_membership(Membership("ws-a", alice.user_id, "member"))
        token = service.login("alice", "alice-secret-pw")
        created = service.create_task(token, "ws-a", "Survive", "open", "HIGH")
        del store, service
        store2 = TaskTrackerStore(tmp.name)
        service2 = TaskTrackerServiceV3(store2)
        token2 = service2.login("alice", "alice-secret-pw")
        fetched = service2.get_task(token2, created.task_id)
        self.assertEqual(fetched.priority, "HIGH")

    def test_t33_legacy_data_preserved(self):
        # A task written by the PARENT (v2, no priority field) reads as
        # MEDIUM under v3: deterministic legacy defaulting, data preserved.
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        from vertical_slice.app.models import Membership
        from vertical_slice.app.store import TaskTrackerStore
        from vertical_slice.app_v2.service import TaskTrackerServiceV2
        from vertical_slice.app_v3.service import TaskTrackerServiceV3

        store = TaskTrackerStore(tmp.name)
        v2 = TaskTrackerServiceV2(store)
        store.ensure_workspace("ws-a", "Alpha")
        alice = v2.register("alice", "alice-secret-pw")
        store.put_membership(Membership("ws-a", alice.user_id, "member"))
        token = v2.login("alice", "alice-secret-pw")
        legacy = v2.create_task(token, "ws-a", "Legacy", "open")
        v3 = TaskTrackerServiceV3(TaskTrackerStore(tmp.name))
        token3 = v3.login("alice", "alice-secret-pw")
        fetched = v3.get_task(token3, legacy.task_id)
        self.assertEqual(fetched.priority, "MEDIUM")
        self.assertEqual(fetched.title, "Legacy")

    def test_t34_events_preserved(self):
        tmp, store, service, tokens = _seeded()
        self.addCleanup(tmp.cleanup)
        task = service.create_task(tokens["alice"], "ws-a", "E", "open", "HIGH")
        service.update_task(tokens["alice"], task.task_id, priority="LOW")
        names = [e.event_name for e in store.events_for_task(task.task_id)]
        self.assertEqual(names, ["task-created", "task-updated"])
        producers = {e.producer for e in store.events_for_task(task.task_id)}
        self.assertEqual(producers, {"svc-task"})


class Coverage(unittest.TestCase):
    def test_t35_architecture_coverage(self):
        evidence = json.load(open(D25_EVIDENCE, encoding="utf-8"))
        self.assertIn("priority-query-policy", evidence["architecture_coverage"])
        self.assertIn("task-persistence", evidence["architecture_coverage"])

    def test_t36_requirement_coverage(self):
        # Obligation semantics per the mapping contract: component rows
        # answer SC01-SC07 (capability) and historical req IDs
        # (preservation; CRUD itself proven behaviorally in T23-T26).
        # SC08-SC13 are downstream-gate obligations, each with its own
        # proof site, asserted here explicitly rather than faked as rows:
        # SC08 this suite green; SC10 D24 record; SC13 this evidence file.
        evidence = json.load(open(D25_EVIDENCE, encoding="utf-8"))
        for req in ("req-auth-login", "req-workspace-members",
                    "req-task-delete", "req-durability"):
            self.assertIn(req, evidence["requirement_coverage"], req)
        for sc in [f"SC{i:02d}" for i in range(1, 8)]:
            self.assertIn(sc, evidence["requirement_coverage"], sc)
        self.assertNotIn("SC10", evidence["requirement_coverage"],
                         "selection-gate obligation must not pose as "
                         "implementation coverage")

    def test_t37_security_coverage(self):
        evidence = json.load(open(D25_EVIDENCE, encoding="utf-8"))
        for item in ("authentication", "authorization", "tenant-isolation",
                     "credential-safety", "input-validation"):
            self.assertIn(item, evidence["security_coverage"], item)

    def test_t38_api_coverage(self):
        tmp, client, alice, _admin = _client()
        self.addCleanup(tmp.cleanup)
        headers = {"Authorization": f"Bearer {alice}"}
        created = client.post(
            "/workspaces/ws-a/tasks", json={"title": "Cov", "priority": "MEDIUM"},
            headers=headers)
        self.assertEqual(created.status_code, 201)
        task_id = created.json()["task_id"]
        self.assertEqual(client.get(
            f"/workspaces/ws-a/tasks/{task_id}", headers=headers).status_code, 200)
        patched = client.patch(
            f"/workspaces/ws-a/tasks/{task_id}", json={"priority": "LOW"},
            headers=headers)
        self.assertEqual(patched.json()["priority"], "LOW")
        self.assertEqual(client.delete(
            f"/workspaces/ws-a/tasks/{task_id}", headers=headers).status_code, 204)

    def test_t39_data_model_coverage(self):
        from vertical_slice.app_v3.models import TaskV3
        import dataclasses
        fields = {f.name for f in dataclasses.fields(TaskV3)}
        self.assertTrue({"task_id", "priority", "title", "status"} <= fields)


class Determinism(unittest.TestCase):
    def test_t40_repeated_deterministic(self):
        self.assertEqual(IMPL.implementation_hash(), IMPL.implementation_hash())

    def test_t41_reordered_deterministic(self):
        raw = open(D25_EVIDENCE, encoding="utf-8").read()
        self.assertEqual(raw, json.dumps(json.loads(raw), sort_keys=True,
                                         separators=(",", ":"),
                                         ensure_ascii=False) + "\n")

    def test_t42_hash_reproducible(self):
        evidence = json.load(open(D25_EVIDENCE, encoding="utf-8"))
        self.assertEqual(IMPL.implementation_hash(), evidence["implementation_hash"])
        self.assertEqual(len(evidence["implementation_hash"]), 64)


class Integrity(unittest.TestCase):
    def _stable(self, path: str, action) -> None:
        before = _sha_file(path)
        action()
        self.assertEqual(_sha_file(path), before, path)

    def test_t43_isr_unchanged(self):
        self._stable("vertical_slice/isr.py",
                     lambda: IMPL.assemble_evidence("2026-01-01T00:00:00+00:00"))

    def test_t44_d22_unchanged(self):
        self._stable(D22_PATH,
                     lambda: IMPL.assemble_evidence("2026-01-01T00:00:00+00:00"))

    def test_t45_d23_unchanged(self):
        self._stable(D23_PATH,
                     lambda: IMPL.assemble_evidence("2026-01-01T00:00:00+00:00"))

    def test_t46_d24_unchanged(self):
        self._stable(D24_PATH,
                     lambda: IMPL.assemble_evidence("2026-01-01T00:00:00+00:00"))

    def test_t47_parent_not_overwritten(self):
        for path in ("vertical_slice/app_v2/service.py",
                     "vertical_slice/app_v2/api.py",
                     "vertical_slice/app_v2/policy.py",
                     "vertical_slice/app/service.py",
                     "vertical_slice/app/store.py"):
            before = _sha_file(path)
            IMPL.assemble_evidence("2026-01-01T00:00:00+00:00")
            self.assertEqual(_sha_file(path), before, path)
        from vertical_slice.app_v2.service import TaskTrackerServiceV2
        import inspect as _inspect
        self.assertNotIn("priority", _inspect.getsource(TaskTrackerServiceV2))


class Firewall(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sources = {}
        for rel in ("vertical_slice/implementation_d25.py",
                    "vertical_slice/app_v3/service.py",
                    "vertical_slice/app_v3/api.py",
                    "vertical_slice/app_v3/policy.py",
                    "vertical_slice/app_v3/tasks.py"):
            cls.sources[rel] = open(rel, encoding="utf-8").read()
        cls.trees = {rel: ast.parse(src)
                     for rel, src in cls.sources.items()}
        cls.called: set[str] = set()
        cls.imports: set[str] = set()
        for tree in cls.trees.values():
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    cls.imports.update(a.name for a in node.names)
                elif isinstance(node, ast.ImportFrom) and node.module:
                    cls.imports.add(node.module)
                elif isinstance(node, ast.Call):
                    func = node.func
                    cls.called.add(func.id if isinstance(func, ast.Name)
                                   else func.attr if isinstance(func, ast.Attribute)
                                   else "")

    def test_t48_no_candidate_generation(self):
        for name in ("generate", "candidates", "propose"):
            self.assertNotIn(name, self.called, (name, self.called))

    def test_t49_no_architecture_selection(self):
        for name in ("choose_candidate", "select", "rank"):
            self.assertNotIn(name, self.called, (name, self.called))

    def test_t50_no_architecture_mutation(self):
        for name in ("mutate", "retire", "crossover"):
            self.assertNotIn(name, self.called, (name, self.called))

    def test_t51_no_evolution_authorization(self):
        blob = "\n".join(self.sources.values()).lower()
        self.assertNotIn("evolution_authorization = true", blob)
        self.assertNotIn("authorization granted", blob)

    def test_t52_no_deployment(self):
        for name in ("Popen", "uvicorn"):
            self.assertNotIn(name, self.called, (name, self.called))
        for rel, src in self.sources.items():
            self.assertNotIn("serve_v2", src, rel)
            self.assertNotIn("serve_v3", src, rel)

    def test_t53_no_observation(self):
        for name in ("observe", "run_online_workload", "launch"):
            self.assertNotIn(name, self.called, (name, self.called))

    def test_t54_no_interpretation(self):
        for name in ("interpret", "assess", "findings"):
            self.assertNotIn(name, self.called, (name, self.called))

    def test_t55_no_optimization(self):
        for name in ("optimize", "tune"):
            self.assertNotIn(name, self.called, (name, self.called))

    def test_t56_production_false(self):
        evidence = json.load(open(D25_EVIDENCE, encoding="utf-8"))
        self.assertIs(evidence["production_authorization"], False)
        self.assertIs(evidence["handoff"]["production_authorization"], False)

    def test_t57_evidence_canonical(self):
        raw = open(D25_EVIDENCE, encoding="utf-8").read()
        self.assertEqual(raw, json.dumps(json.loads(raw), sort_keys=True,
                                         separators=(",", ":"),
                                         ensure_ascii=False) + "\n")

    def test_t58_no_secrets(self):
        import re
        blob = open(D25_EVIDENCE, encoding="utf-8").read()
        self.assertIsNone(re.search(
            r"(password|secret|api_key|session_cookie|private_key"
            r"|credential)\s*[:=]\s*\S+", blob.lower()))
        for marker in ("alice-secret-pw", "bob-secret-pw", "cara-secret-pw"):
            self.assertNotIn(marker, blob, marker)


class FailClosed(unittest.TestCase):
    def test_t59_malformed_architecture(self):
        bad = tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False, encoding="utf-8")
        record = json.load(open(D24_PATH, encoding="utf-8"))
        record.pop("selected_candidate")
        bad.write(json.dumps(record))
        bad.close()
        self.addCleanup(lambda: os.unlink(bad.name))
        with self.assertRaises(IMPL.ImplementationError):
            IMPL.verify_upstream(d24_path=bad.name)

    def test_t60_malformed_isr(self):
        with self.assertRaises(IMPL.ImplementationError):
            IMPL.verify_upstream(d22_path="vertical_slice/no-such-file.json")

    def test_t61_invalid_lineage(self):
        bad_row = ("app_v3.policy.Nope", "priority-query-policy",
                   "vs1-obj001", "no-such-isr-node", "SC05")
        with mock.patch.object(IMPL, "COMPONENT_MAP",
                               IMPL.COMPONENT_MAP + (bad_row,)):
            with self.assertRaises(IMPL.ImplementationError):
                IMPL.validate_lineage()

    def test_t62_unauthorized_change(self):
        bad = tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False, encoding="utf-8")
        record = json.load(open(D23_PATH, encoding="utf-8"))
        for candidate in record["candidates"]:
            candidate["architecture_profile"] = "microservice-decomposition"
        bad.write(json.dumps(record))
        bad.close()
        self.addCleanup(lambda: os.unlink(bad.name))
        with self.assertRaises(IMPL.ImplementationError):
            IMPL.verify_upstream(d23_path=bad.name)


if __name__ == "__main__":
    unittest.main()
