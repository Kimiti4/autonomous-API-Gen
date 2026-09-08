"""VS-D05 tests T01-T15: controlled deployment + bring-up (local loopback)."""
from __future__ import annotations

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


class DeployedServer(unittest.TestCase):
    @classmethod
    def launch(cls, store_dir: str) -> tuple[subprocess.Popen, str]:
        env = dict(os.environ, VS1_STORE_DIR=store_dir, VS1_PORT="0",
                   PYTHONDONTWRITEBYTECODE="1")
        proc = subprocess.Popen(
            [sys.executable, "-m", "vertical_slice.serve"],
            env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, cwd=os.getcwd())
        assert proc.stdout is not None
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
            raise AssertionError("server did not report a bound port")
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
        raise AssertionError("readiness condition never satisfied")

    @classmethod
    def shutdown(cls, proc: subprocess.Popen) -> int | None:
        proc.terminate()
        try:
            return proc.wait(timeout=15)
        except subprocess.TimeoutExpired:
            proc.kill()
            return proc.wait(timeout=15)

    def prepare(self, store_dir: str) -> dict[str, str]:
        """Deployment seeding BEFORE server start (setup, not product
        behavior): workspace, users, and first memberships are written
        directly so the server loads complete state at startup. The server
        process must not be running yet (its store is in-memory)."""
        from vertical_slice.app.models import Membership
        from vertical_slice.app.service import TaskTrackerService
        from vertical_slice.app.store import TaskTrackerStore

        state = {"n": 0}

        def generate() -> str:
            state["n"] += 1
            return f"vs1-deploy-token-{state['n']:04d}"

        store = TaskTrackerStore(store_dir)
        service = TaskTrackerService(store, token_generator=generate)
        store.ensure_workspace("ws-a", "Alpha")
        store.ensure_workspace("ws-b", "Beta")
        alice = service.register("alice", "alice-secret-pw")
        bob = service.register("bob", "bob-secret-pw")
        admin = service.register("cara-admin", "cara-secret-pw")
        store.put_membership(Membership("ws-a", alice.user_id, "member"))
        store.put_membership(Membership("ws-a", admin.user_id, "admin"))
        store.put_membership(Membership("ws-b", bob.user_id, "member"))
        return {
            "alice": service.login("alice", "alice-secret-pw"),
            "bob": service.login("bob", "bob-secret-pw"),
            "admin": service.login("cara-admin", "cara-secret-pw"),
            "alice_id": alice.user_id,
            "bob_id": bob.user_id,
            "admin_id": admin.user_id,
        }

    def run_deployed(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self._store_dir = tmp.name
        tokens = self.prepare(tmp.name)
        proc, base = self.launch(tmp.name)
        self.addCleanup(lambda: self.shutdown(proc))
        return base, tokens


class TestT01FrozenInputs(DeployedServer):
    def test_refuses_stale_inputs(self):
        from vertical_slice import implementation as IMPL
        identity = IMPL.frozen_input_identity()
        self.assertEqual(identity["vs-d03-selected"], "vs1-candidate-a")
        self.assertEqual(
            identity["vs-d01-graph-sha256"],
            "28548494e754e9b8214e9f72511a7ba0187fa3378264306a82ff8868bd2e5526")
        self.assertEqual(
            identity["vs-d02-isr-content-hash"],
            "48e53dcef47aad84e52e20ec116f5b1f9616a626f42d1c281e3cc26cdf8e9dfb")


class TestT02CandidateIdentity(DeployedServer):
    def test_bound_to_candidate_a(self):
        from vertical_slice.deployment import CANDIDATE_ID, build_contract
        self.assertEqual(CANDIDATE_ID, "vs1-candidate-a")
        self.assertEqual(build_contract()["candidate_id"], "vs1-candidate-a")


class TestT03ImplementationIdentity(DeployedServer):
    def test_uses_d04_implementation(self):
        from vertical_slice import implementation as IMPL
        self.assertEqual(IMPL.IMPLEMENTATION_VERSION, "vs1-impl-v1")
        evidence = IMPL.build_evidence()
        self.assertEqual(evidence["candidate_id"], "vs1-candidate-a")


class TestT04Configuration(DeployedServer):
    def test_config_bounded(self):
        from vertical_slice.deployment import HOST, TARGET, build_contract
        self.assertEqual(HOST, "127.0.0.1")
        self.assertEqual(TARGET, "local-uvicorn-loopback")
        contract = build_contract()
        self.assertEqual(contract["host"], "127.0.0.1")
        self.assertNotIn("0.0.0.0", json.dumps(contract))


class TestT05Dependencies(DeployedServer):
    def test_versions_available(self):
        import fastapi
        import uvicorn
        import pydantic
        from vertical_slice.deployment import DEPENDENCY_VERSIONS
        installed = {"fastapi": fastapi.__version__, "uvicorn": uvicorn.__version__,
                     "pydantic": pydantic.__version__}
        for name, version, _purpose, required in DEPENDENCY_VERSIONS:
            if name in installed and required == "required" and version != "installed":
                self.assertEqual(installed[name], version, name)


class TestT06Startup(DeployedServer):
    def test_server_starts(self):
        base, _tokens = self.run_deployed()
        self.assertTrue(base.startswith("http://127.0.0.1:"))


class TestT07Readiness(DeployedServer):
    def test_health_body(self):
        base, _tokens = self.run_deployed()
        status, body = _http("GET", base + "/health")
        self.assertEqual(status, 200)
        self.assertEqual(body, {"status": "ok"})


class TestT08APIReachability(DeployedServer):
    def test_crud_reachable(self):
        base, tokens = self.run_deployed()
        headers_status, _ = _http("GET", base + "/workspaces/ws-a/tasks",
                                  token=tokens["alice"])
        self.assertEqual(headers_status, 200)
        status, created = _http("POST", base + "/workspaces/ws-a/tasks",
                                {"title": "Reachable"}, token=tokens["alice"])
        self.assertEqual(status, 201)
        status, _ = _http("GET", base + f"/workspaces/ws-a/tasks/{created['task_id']}",
                          token=tokens["alice"])
        self.assertEqual(status, 200)


class TestT09Security(DeployedServer):
    def test_runtime_policies_hold(self):
        base, tokens = self.run_deployed()
        status, _ = _http("GET", base + "/workspaces/ws-a/tasks")
        self.assertEqual(status, 401)
        # fresh outsider (not a member) must be isolated from ws-a
        status, eve = _http("POST", base + "/users/register",
                            {"username": "eve", "password": "eve-secret-pw"})
        self.assertEqual(status, 201)
        status, body = _http("POST", base + "/users/login",
                             {"username": "eve", "password": "eve-secret-pw"})
        status, _ = _http("GET", base + "/workspaces/ws-a/tasks", token=body["token"])
        self.assertEqual(status, 403)


class TestT10Persistence(DeployedServer):
    def test_persistence_across_restart(self):
        import tempfile
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        tokens = self.prepare(tmp.name)
        proc, base = self.launch(tmp.name)
        try:
            status, created = _http(
                "POST", base + "/workspaces/ws-a/tasks",
                {"title": "Survive restart"}, token=tokens["alice"])
            self.assertEqual(status, 201)
            task_id = created["task_id"]
        finally:
            self.shutdown(proc)
        proc2, base2 = self.launch(tmp.name)
        try:
            status, body = _http("POST", base2 + "/users/login",
                                 {"username": "alice", "password": "alice-secret-pw"})
            self.assertEqual(status, 200)
            status, fetched = _http(
                "GET", base2 + f"/workspaces/ws-a/tasks/{task_id}", token=body["token"])
            self.assertEqual(status, 200)
            self.assertEqual(fetched["title"], "Survive restart")
        finally:
            self.shutdown(proc2)


class TestT11Events(DeployedServer):
    def test_event_wiring(self):
        import json as json_module
        import os
        base, tokens = self.run_deployed()
        status, created = _http("POST", base + "/workspaces/ws-a/tasks",
                                {"title": "Eventful"}, token=tokens["alice"])
        task_id = created["task_id"]
        status, _ = _http("PATCH", base + f"/workspaces/ws-a/tasks/{task_id}",
                          {"status": "done"}, token=tokens["alice"])
        self.assertEqual(status, 200)
        with open(os.path.join(self._store_dir, "store.json"), encoding="utf-8") as f:
            state = json_module.load(f)
        names = [e["event_name"] for e in state["events"] if e["task_id"] == task_id]
        self.assertEqual(names, ["task-created", "task-updated"])
        self.assertTrue(all(e["producer"] == "svc-task" for e in state["events"]
                            if e["task_id"] == task_id))


class TestT12Shutdown(DeployedServer):
    def test_shutdown_clean(self):
        import tempfile
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        proc, base = self.launch(tmp.name)
        status, _ = _http("GET", base + "/health")
        self.assertEqual(status, 200)
        code = self.shutdown(proc)
        self.assertIsNotNone(code)
        with self.assertRaises(OSError):
            _http("GET", base + "/health")


class TestT13Evidence(DeployedServer):
    def test_evidence_valid(self):
        import json as json_module
        import os
        path = os.path.join("vertical_slice", "deployment_evidence.json")
        with open(path, encoding="utf-8") as f:
            evidence = json_module.load(f)
        for field in ("deployment_contract_version", "deployment_id", "candidate_id",
                      "implementation_version", "vs-d01-graph-sha256",
                      "vs-d02-isr-content-hash", "vs-d03-selected",
                      "deployment_target", "runtime_version", "dependency_versions",
                      "startup_result", "readiness_result", "smoke_test_results",
                      "shutdown_result"):
            self.assertIn(field, evidence, field)
        self.assertEqual(evidence["candidate_id"], "vs1-candidate-a")
        self.assertEqual(
            evidence["vs-d01-graph-sha256"],
            "28548494e754e9b8214e9f72511a7ba0187fa3378264306a82ff8868bd2e5526")
        self.assertEqual(
            evidence["vs-d02-isr-content-hash"],
            "48e53dcef47aad84e52e20ec116f5b1f9616a626f42d1c281e3cc26cdf8e9dfb")


class TestT14Determinism(DeployedServer):
    def test_contract_reproducible(self):
        from vertical_slice.deployment import build_contract
        self.assertEqual(build_contract(), build_contract())


class TestT15Boundary(DeployedServer):
    def test_no_observation_evolution_work(self):
        import ast
        import os
        for rel in (os.path.join("vertical_slice", "serve.py"),
                    os.path.join("vertical_slice", "deployment.py")):
            src = open(rel, encoding="utf-8").read()
            tree = ast.parse(src)
            imports: set[str] = set()
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    imports.update(a.name.split(".")[0] for a in node.names)
                elif isinstance(node, ast.ImportFrom) and node.module:
                    imports.add(node.module.split(".")[0])
            self.assertLessEqual(
                imports,
                {"__future__", "os", "typing", "uvicorn", "vertical_slice"},
                (rel, imports))
            lowered = src.lower()
            for token in ("telemetry", "evolution", "compiler", "docker",
                          "prometheus", "opentelemetry"):
                self.assertNotIn(token, lowered, (rel, token))


if __name__ == "__main__":
    unittest.main()
