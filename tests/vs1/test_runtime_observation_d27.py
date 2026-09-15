"""VS-D27 tests: runtime observation of the D26 deployment artifact.

Loopback fixture only (explicit D27 authorization scope); mechanical
facts, no interpretation. Process lifecycle owned by the harness, never
by the observation module.
"""
from __future__ import annotations

import ast
import json
import os
import re
import subprocess
import sys
import tempfile
import time
import unittest
import urllib.request
import urllib.error


def _http(method: str, url: str, body: object = None,
          token: str | None = None) -> tuple[int, object]:
    data = None
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    if body is not None:
        data = json.dumps(body).encode()
    request = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            raw = response.read().decode()
            return response.status, json.loads(raw) if raw else None
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode()
        try:
            return exc.code, json.loads(raw) if raw else None
        except ValueError:
            return exc.code, raw


class DeployedServerV3(unittest.TestCase):
    _LAUNCHED: list = []

    @classmethod
    def launch(cls, store_dir: str):
        env = dict(os.environ, VS1_STORE_DIR=store_dir, VS1_PORT="0",
                   PYTHONDONTWRITEBYTECODE="1")
        proc = subprocess.Popen(
            [sys.executable, "-m", "vertical_slice.serve_v3"],
            env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, cwd=os.getcwd())
        cls._LAUNCHED.append(proc)
        assert proc.stdout is not None
        assert "vertical_slice.serve_v3" in proc.args, proc.args
        assert "vertical_slice.serve" not in proc.args, proc.args
        assert "vertical_slice.serve_v2" not in proc.args, proc.args
        base = ""
        deadline = time.time() + 30
        port_pattern = re.compile(r"Uvicorn running on http://127\.0\.0\.1:(\d+)")
        while time.time() < deadline:
            line = proc.stdout.readline()
            if not line:
                break
            match = port_pattern.search(line)
            if match:
                base = f"http://127.0.0.1:{match.group(1)}"
                break
        if not base or proc.poll() is not None:
            proc.kill()
            raise AssertionError("v3 server did not report a bound port")
        ready_deadline = time.time() + 20
        while time.time() < ready_deadline:
            try:
                status, _ = _http("GET", base + "/health")
                if status == 200:
                    return proc, base
            except OSError:
                pass
            time.sleep(0.2)
        proc.kill()
        raise AssertionError("v3 readiness never satisfied")

    @classmethod
    def shutdown(cls, proc) -> int | None:
        proc.terminate()
        try:
            return proc.wait(timeout=15)
        except subprocess.TimeoutExpired:
            proc.kill()
            return proc.wait(timeout=15)

    def seed(self, store_dir: str) -> str:
        from vertical_slice.app.models import Membership
        from vertical_slice.app_v3.service import TaskTrackerServiceV3
        from vertical_slice.app.store import TaskTrackerStore

        store = TaskTrackerStore(store_dir)
        service = TaskTrackerServiceV3(store)
        store.ensure_workspace("ws-obs", "Observed")
        admin = service.register("setup-admin", "a" * 16)
        store.put_membership(Membership("ws-obs", admin.user_id, "admin"))
        return service.login("setup-admin", "a" * 16)


def _transport(base: str):
    def call(method: str, url: str, body: object = None,
             token: str | None = None) -> tuple[int, object]:
        return _http(method, url, body, token)
    return call


class DeploymentIdentity(DeployedServerV3):
    def test_identity_gate(self):
        from vertical_slice import runtime_observation_d27 as OBS27
        identity = OBS27.verify_deployment_identity()
        self.assertEqual(identity["deployment_id"],
                         "vs1-deploy-obj001-4ca3d24c13561599")
        self.assertEqual(identity["implementation_id"], "vs1-impl-obj001-v1")
        self.assertEqual(identity["implementation_hash"],
                         "7dbbf34fe75660f1aa7355e7fc68d7d427467f0d8e2278e29357e666d30207f4")
        self.assertEqual(identity["architecture_id"],
                         "vs1-obj001-candidate-313b071dd7d4")
        self.assertEqual(identity["manifest_hash"],
                         "31a7d9fc0aefe7d095c60593f12480313b4474165130f237d1c03e1af33de382")

    def test_v3_process_only(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.seed(tmp.name)
        proc, base = self.launch(tmp.name)
        try:
            self.assertIn("vertical_slice.serve_v3", proc.args)
            status, body = _http("GET", base + "/health")
            self.assertEqual((status, body), (200, {"status": "ok"}))
        finally:
            self.shutdown(proc)


class PriorityWorkload(DeployedServerV3):
    EXECUTION_ID = "vs1-d27-test-run"

    @classmethod
    def setUpClass(cls):
        from vertical_slice import runtime_observation_d27 as OBS27
        cls._tmp = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls._tmp.cleanup)
        cls._admin = cls.seed(cls, cls._tmp.name)
        cls._proc, cls._base = cls.launch(cls._tmp.name)
        cls.addClassCleanup(lambda: cls.shutdown(cls._proc))
        cls._records = OBS27.run_priority_workload(
            cls._base, cls.EXECUTION_ID, _transport(cls._base), cls._admin)
        cls._by_id = {r["observation_id"]: r for r in cls._records}

    def _assert_pass(self, observation_id: str, expected_class: str):
        record = self._by_id[observation_id]
        self.assertEqual(record["observed_class"], expected_class, observation_id)
        self.assertEqual(record["status"], "PASS", observation_id)

    def test_readiness(self):
        self._assert_pass("lifecycle.readiness", "http-200")

    def test_auth(self):
        self._assert_pass("auth.register", "http-201")
        self._assert_pass("auth.login", "http-200")
        self._assert_pass("auth.invalid-rejected", "http-401")
        self._assert_pass("auth.authenticated-request", "http-200")

    def test_priority_create(self):
        self._assert_pass("priority.create-low", "http-201")
        self._assert_pass("priority.create-medium", "http-201")
        self._assert_pass("priority.create-high", "http-201")

    def test_priority_reject(self):
        self._assert_pass("priority.invalid-rejected", "http-422")
        self._assert_pass("priority.filter-invalid-rejected", "http-422")

    def test_priority_filter(self):
        self._assert_pass("priority.filter-high", "http-200")
        self._assert_pass("priority.filter-low", "http-200")

    def test_priority_update_read(self):
        self._assert_pass("priority.update", "http-200")
        self._assert_pass("crud.read-after-update", "http-200")

    def test_authz(self):
        self._assert_pass("authz.admin-grant", "http-201")
        self._assert_pass("authz.permitted-operation", "http-201")
        self._assert_pass("authz.outsider-rejected", "http-403")
        self._assert_pass("authz.role-rejected", "http-403")

    def test_crud_close(self):
        self._assert_pass("crud.delete", "http-204")
        self._assert_pass("crud.read-after-delete", "http-422")

    def test_latency_measured_not_judged(self):
        measurement = self._by_id["lifecycle.readiness"]["measurement"]
        self.assertIn("latency_ms", measurement)
        self.assertIsInstance(measurement["latency_ms"], float)

    def test_no_secrets_recorded(self):
        from vertical_slice import runtime_observation_d27 as OBS27
        for record in self._records:
            OBS27.OBS.assert_secret_safe(record)


class LifecycleEvidence(DeployedServerV3):
    def test_events_restart_shutdown(self):
        from vertical_slice import runtime_observation_d27 as OBS27
        execution_id = "vs1-d27-test-lifecycle"
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        admin = self.seed(tmp.name)
        proc, base = self.launch(tmp.name)
        try:
            records = OBS27.run_priority_workload(
                base, execution_id, _transport(base), admin)
            with open(os.path.join(tmp.name, "store.json"),
                      encoding="utf-8") as f:
                state = json.load(f)
            created = [e for e in state["events"]
                       if e["event_name"] == "task-created"]
            self.assertTrue(created)
            self.assertTrue(all(e["producer"] == "svc-task" for e in created))
            records.append(OBS27.observe(
                observation_id="events.lifecycle-emitted",
                execution_id=execution_id, operation="store.events-read",
                expected_class="lifecycle-events",
                observed_class="lifecycle-events", status="PASS",
                measurement={"event_count": len(created)}))
        finally:
            code1 = self.shutdown(proc)
        proc2, base2 = self.launch(tmp.name)
        try:
            status, body = _http("POST", base2 + "/users/login",
                                 {"username": "setup-admin",
                                  "password": "a" * 16})
            self.assertEqual(status, 200)
            status, tasks = _http("GET", base2 + "/workspaces/ws-obs/tasks",
                                  token=body["token"])
            self.assertEqual(status, 200)
            # setup-admin is admin of ws-obs: sees all tasks incl.
            # priorities. Pre-restart the workload updated Prio LOW →
            # HIGH and deleted Prio MEDIUM; both must have persisted.
            by_title = {t["title"]: t.get("priority") for t in tasks}
            self.assertEqual(by_title.get("Prio HIGH"), "HIGH")
            self.assertEqual(by_title.get("Prio LOW"), "HIGH")
            self.assertNotIn("Prio MEDIUM", by_title)
            records.append(OBS27.observe(
                observation_id="persist.restart-state",
                execution_id=execution_id,
                operation="lifecycle.restart-persist",
                expected_class="state-preserved",
                observed_class="state-preserved", status="PASS",
                measurement={"http_status": status,
                             "task_count": len(tasks)}))
        finally:
            code2 = self.shutdown(proc2)
        try:
            _http("GET", base2 + "/health")
            post = "reachable"
        except OSError:
            post = "refused"
        self.assertIsNotNone(code1)
        self.assertIsNotNone(code2)
        self.assertEqual(post, "refused")
        records.append(OBS27.observe(
            observation_id="lifecycle.shutdown-clean",
            execution_id=execution_id, operation="lifecycle.shutdown",
            expected_class="shutdown-clean", observed_class="shutdown-clean",
            status="PASS", measurement={"clean_shutdowns": 2}))
        by_id = {r["observation_id"]: r for r in records}
        self.assertEqual(by_id["persist.restart-state"]["status"], "PASS")
        self.assertEqual(by_id["lifecycle.shutdown-clean"]["status"], "PASS")


class MechanicsFirewall(unittest.TestCase):
    def test_normalization(self):
        from vertical_slice import runtime_observation_d27 as OBS27
        first = OBS27.observe(
            observation_id="unit.probe", operation="http.probe",
            expected_class="http-200", observed_class="http-200",
            status="PASS", measurement={"http_status": 200, "latency_ms": 1.5})
        second = OBS27.observe(
            observation_id="unit.probe", operation="http.probe",
            expected_class="http-200", observed_class="http-200",
            status="PASS", measurement={"http_status": 200, "latency_ms": 99.9})
        self.assertEqual(OBS27.OBS.normalize_record(first),
                         OBS27.OBS.normalize_record(second))

    def test_fail_closed(self):
        from vertical_slice import runtime_observation_d27 as OBS27
        with self.assertRaises(Exception):
            OBS27.observe(observation_id="unit.bad", operation="http.probe",
                          expected_class="http-200", observed_class="http-200",
                          status="ALMOST")
        with self.assertRaises(Exception):
            OBS27.observe(observation_id="unit.bad", operation="http.probe",
                          expected_class="http-200", observed_class=None,
                          status="PASS")

    def test_firewall(self):
        import vertical_slice.runtime_observation_d27 as module
        tree = ast.parse(open(module.__file__, encoding="utf-8").read())
        imports: set[str] = set()
        called: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.update(a.name for a in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imports.add(node.module)
            elif isinstance(node, ast.Call):
                func = node.func
                called.add(func.id if isinstance(func, ast.Name)
                           else func.attr if isinstance(func, ast.Attribute)
                           else "")
        # Read-only consumption of D25/D26/D17-observation contracts only.
        self.assertLessEqual(imports, {"__future__", "hashlib", "json", "time",
                                       "typing", "pathlib", "vertical_slice"},
                             imports)
        for name in ("choose_candidate", "decide", "deploy", "interpret",
                     "optimize", "authorize", "Popen", "evolve", "compile",
                     "retire", "mutate"):
            self.assertNotIn(name, called, (name, called))

    def test_upstream_immutable(self):
        from vertical_slice import implementation_d25 as IMPLD25
        evidence = IMPLD25.assemble_evidence("2026-01-01T00:00:00+00:00")
        self.assertEqual(evidence["implementation_hash"],
                         "7dbbf34fe75660f1aa7355e7fc68d7d427467f0d8e2278e29357e666d30207f4")

    def test_evidence_provenance(self):
        evidence = json.load(open(
            "vertical_slice/runtime_observation_d27_evidence.json",
            encoding="utf-8"))
        self.assertEqual(evidence["contract"], "vs1-runtime-observe-d27")
        self.assertEqual(evidence["deployment_id"],
                         "vs1-deploy-obj001-4ca3d24c13561599")
        self.assertEqual(evidence["implementation_id"], "vs1-impl-obj001-v1")
        self.assertEqual(evidence["architecture_id"],
                         "vs1-obj001-candidate-313b071dd7d4")
        self.assertEqual(evidence["summary"]["status_counts"]["FAIL"], 0)
        self.assertIn("normalized_hash", evidence)

    def test_no_orphan_processes(self):
        orphans = [p for p in DeployedServerV3._LAUNCHED if p.poll() is None]
        self.assertEqual(orphans, [])


if __name__ == "__main__":
    unittest.main()
