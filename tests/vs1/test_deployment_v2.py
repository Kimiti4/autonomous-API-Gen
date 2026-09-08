"""VS-D16 tests T01-T31: regenerated-implementation deployment bring-up.

Controlled transition vs1-impl-v2 -> running loopback deployment. Consumes
upstream authority read-only; performs no observation, interpretation, or
evolution work. Live-server tests use per-run isolated stores and ports.
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


EXPECTED_IMPL_HASH = (
    "d2090df69127e9922494bb7a4d526de087fd948ee793bdf326d5fe18fac1dd8c"
)
EXPECTED_ARCH = "vs1-evolved-96fe2d29fd76"
EXPECTED_ARCH_HASH = (
    "d0f8d7579a08de83e9490f373e6f1df70d44a546a1a8385cd27444516f724631"
)
EXPECTED_SELECTION_HASH = (
    "f39c508e3a6ed52dbdd1b57766706804277e4cf70d12509f71f589370f549d1b"
)
EXPECTED_ISR = "48e53dcef47aad84e52e20ec116f5b1f9616a626f42d1c281e3cc26cdf8e9dfb"
EXPECTED_GRAPH = (
    "28548494e754e9b8214e9f72511a7ba0187fa3378264306a82ff8868bd2e5526"
)


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


class DeployedServerV2(unittest.TestCase):
    """Loopback bring-up harness for the v2 namespace only."""

    _LAUNCHED: list[subprocess.Popen] = []

    @classmethod
    def launch(cls, store_dir: str) -> tuple[subprocess.Popen, str]:
        env = dict(os.environ, VS1_STORE_DIR=store_dir, VS1_PORT="0",
                   PYTHONDONTWRITEBYTECODE="1")
        proc = subprocess.Popen(
            [sys.executable, "-m", "vertical_slice.serve_v2"],
            env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, cwd=os.getcwd())
        cls._LAUNCHED.append(proc)
        assert proc.stdout is not None
        # Fail closed: the process must be the v2 entrypoint, never v1.
        assert "vertical_slice.serve_v2" in proc.args, proc.args
        assert "vertical_slice.serve" not in proc.args, proc.args
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
            raise AssertionError("v2 server did not report a bound port")
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
        raise AssertionError("v2 readiness condition never satisfied")

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
        behavior): workspaces, users, and first memberships are written
        directly so the v2 server loads complete state at startup."""
        from vertical_slice.app.models import Membership
        from vertical_slice.app_v2.service import TaskTrackerServiceV2
        from vertical_slice.app.store import TaskTrackerStore

        state = {"n": 0}

        def generate() -> str:
            state["n"] += 1
            return f"vs1-deploy-v2-token-{state['n']:04d}"

        store = TaskTrackerStore(store_dir)
        service = TaskTrackerServiceV2(store, token_generator=generate)
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


class TestT01SelectedArchitecture(DeployedServerV2):
    def test_d14_resolves(self):
        from vertical_slice import regeneration as REG
        selection = REG.load_selection()
        self.assertEqual(selection["selected_candidate_id"], EXPECTED_ARCH)
        self.assertEqual(selection["selection_hash"], EXPECTED_SELECTION_HASH)


class TestT02ImplementationResolves(DeployedServerV2):
    def test_d15_resolves(self):
        from vertical_slice import regeneration as REG
        evidence = REG.build_evidence()
        self.assertEqual(evidence["implementation_id"], "vs1-impl-v2")
        self.assertEqual(evidence["parent_implementation_id"], "vs1-impl-v1")
        self.assertEqual(evidence["selected_architecture_id"], EXPECTED_ARCH)


class TestT03ImplementationHash(DeployedServerV2):
    def test_hash_matches(self):
        from vertical_slice import regeneration as REG
        self.assertEqual(REG.build_evidence()["implementation_hash"],
                         EXPECTED_IMPL_HASH)


class TestT04ISRHash(DeployedServerV2):
    def test_isr_matches(self):
        from vertical_slice import implementation as IMPL
        identity = IMPL.frozen_input_identity()
        self.assertEqual(identity["vs-d02-isr-content-hash"], EXPECTED_ISR)
        self.assertEqual(identity["vs-d01-graph-sha256"], EXPECTED_GRAPH)


class TestT05D12NoChange(DeployedServerV2):
    def test_real_decision_stands(self):
        with open("vertical_slice/evolution_decision_v2_evidence.json",
                  encoding="utf-8") as f:
            decision = json.load(f)
        self.assertEqual(decision.get("decision"), "NO_CHANGE")


class TestT06ProductionFalse(DeployedServerV2):
    def test_no_production_authorization(self):
        from vertical_slice import deployment_v2 as DEP
        from vertical_slice import regeneration as REG
        self.assertIs(DEP.PRODUCTION_AUTHORIZATION, False)
        self.assertIs(DEP.build_contract()["production_authorization"], False)
        self.assertIs(REG.load_selection()["production_authorization"], False)
        self.assertIs(REG.build_evidence()["production_authorization"], False)


class TestT07V1Untouched(DeployedServerV2):
    def test_parent_implementation_intact(self):
        from vertical_slice import implementation as IMPL
        from vertical_slice.app import service as V1
        self.assertEqual(IMPL.IMPLEMENTATION_VERSION, "vs1-impl-v1")
        evidence = IMPL.build_evidence()
        self.assertEqual(evidence["candidate_id"], "vs1-candidate-a")
        self.assertEqual(V1.TaskTrackerService.__module__,
                         "vertical_slice.app.service")


class TestT08V2Entrypoint(DeployedServerV2):
    def test_v2_selected(self):
        from vertical_slice import deployment_v2 as DEP
        self.assertEqual(DEP.LAUNCH_MODULE, "vertical_slice.serve_v2")
        self.assertTrue(DEP.ENTRYPOINT.startswith("vertical_slice/app_v2/"))
        self.assertEqual(DEP.ENTRYPOINT_NAMESPACE, "vertical_slice.app_v2")
        identity = DEP.verify_implementation()
        self.assertEqual(identity["implementation_id"], "vs1-impl-v2")


class TestT09ContractDeterministic(DeployedServerV2):
    def test_repeated_preparation_identical(self):
        from vertical_slice import deployment_v2 as DEP
        first, second = DEP.build_contract(), DEP.build_contract()
        self.assertEqual(first, second)
        self.assertEqual(DEP.contract_hash(first), DEP.contract_hash(second))


class TestT10ConfigurationCanonical(DeployedServerV2):
    def test_config_bounded(self):
        from vertical_slice import deployment_v2 as DEP
        contract = DEP.build_contract()
        runtime = DEP.runtime_configuration()
        self.assertEqual(contract["deployment_target"], "local-uvicorn-loopback")
        self.assertEqual(runtime["host"], "127.0.0.1")
        self.assertNotIn("0.0.0.0", json.dumps(contract))
        for key in ("host", "application_entrypoint", "database_configuration",
                    "runtime_environment", "security_configuration",
                    "logging_configuration"):
            self.assertIn(key, runtime, key)
        self.assertIsNone(re.search(
            r"(password|secret|api_key|session_cookie|private_key"
            r"|credential)\s*[:=]\s*\S+", json.dumps(contract).lower()))


class TestT11Startup(DeployedServerV2):
    def test_server_starts(self):
        base, _tokens = self.run_deployed()
        self.assertTrue(base.startswith("http://127.0.0.1:"))


class TestT12Readiness(DeployedServerV2):
    def test_health_body(self):
        base, _tokens = self.run_deployed()
        status, body = _http("GET", base + "/health")
        self.assertEqual(status, 200)
        self.assertEqual(body, {"status": "ok"})


class TestT13APIReachable(DeployedServerV2):
    def test_crud_reachable(self):
        base, tokens = self.run_deployed()
        status, _ = _http("GET", base + "/workspaces/ws-a/tasks",
                          token=tokens["alice"])
        self.assertEqual(status, 200)
        status, created = _http("POST", base + "/workspaces/ws-a/tasks",
                                {"title": "Reachable"}, token=tokens["alice"])
        self.assertEqual(status, 201)
        status, _ = _http(
            "GET", base + f"/workspaces/ws-a/tasks/{created['task_id']}",
            token=tokens["alice"])
        self.assertEqual(status, 200)


class TestT14ValidRequest(DeployedServerV2):
    def test_controlled_valid_request(self):
        base, tokens = self.run_deployed()
        status, created = _http("POST", base + "/workspaces/ws-a/tasks",
                                {"title": "Smoke valid", "status": "open"},
                                token=tokens["alice"])
        self.assertEqual(status, 201)
        self.assertEqual(created["title"], "Smoke valid")
        self.assertEqual(created["workspace_id"], "ws-a")
        self.assertEqual(set(created),
                         {"task_id", "workspace_id", "title", "status",
                          "owner_id", "assignee_id"})


class TestT15Rejection(DeployedServerV2):
    def test_controlled_rejection(self):
        base, tokens = self.run_deployed()
        status, _ = _http("GET", base + "/workspaces/ws-a/tasks")
        self.assertEqual(status, 401)
        status, eve = _http("POST", base + "/users/register",
                            {"username": "eve", "password": "eve-secret-pw"})
        self.assertEqual(status, 201)
        status, body = _http("POST", base + "/users/login",
                             {"username": "eve", "password": "eve-secret-pw"})
        self.assertEqual(status, 200)
        status, _ = _http("GET", base + "/workspaces/ws-a/tasks",
                          token=body["token"])
        self.assertEqual(status, 403)


class TestT16Persistence(DeployedServerV2):
    def test_persistence_connectivity(self):
        base, tokens = self.run_deployed()
        status, created = _http("POST", base + "/workspaces/ws-a/tasks",
                                {"title": "Persist me"}, token=tokens["alice"])
        self.assertEqual(status, 201)
        with open(os.path.join(self._store_dir, "store.json"),
                  encoding="utf-8") as f:
            state = json.load(f)
        self.assertIn(created["task_id"], state["tasks"])
        self.assertEqual(state["tasks"][created["task_id"]]["title"],
                         "Persist me")


class TestT17SecurityPolicy(DeployedServerV2):
    def test_central_policy_active(self):
        base, tokens = self.run_deployed()
        # identical-error login: unknown user and wrong password both 401
        status, _ = _http("POST", base + "/users/login",
                          {"username": "nobody", "password": "x"})
        self.assertEqual(status, 401)
        status, _ = _http("POST", base + "/users/login",
                          {"username": "alice", "password": "wrong-pw"})
        self.assertEqual(status, 401)
        # role path: member cannot manage membership, admin can
        status, _ = _http("POST", base + "/workspaces/ws-a/members",
                          {"user_id": tokens["bob_id"]}, token=tokens["alice"])
        self.assertEqual(status, 403)
        status, body = _http("POST", base + "/workspaces/ws-a/members",
                             {"user_id": tokens["bob_id"], "role": "member"},
                             token=tokens["admin"])
        self.assertEqual(status, 201)
        self.assertEqual(body["role"], "member")
        # tenant isolation holds through the v2 boundary (use a true
        # outsider: bob was just granted ws-a membership above)
        status, _ = _http("POST", base + "/users/register",
                          {"username": "mallory",
                           "password": "mallory-secret-pw"})
        self.assertEqual(status, 201)
        status, mallory = _http("POST", base + "/users/login",
                                {"username": "mallory",
                                 "password": "mallory-secret-pw"})
        self.assertEqual(status, 200)
        status, _ = _http("GET", base + "/workspaces/ws-a/tasks",
                          token=mallory["token"])
        self.assertEqual(status, 403)


class TestT18NoSecretLeakage(DeployedServerV2):
    def test_secret_shapes_absent(self):
        base, tokens = self.run_deployed()
        bodies: list[object] = []
        for method, path, payload, token in (
                ("GET", "/health", None, None),
                ("POST", "/users/register",
                 {"username": "leakcheck", "password": "leakcheck-pw"}, None),
                ("POST", "/users/login",
                 {"username": "alice", "password": "alice-secret-pw"}, None),
                ("GET", "/workspaces/ws-a/tasks", None, tokens["alice"])):
            _status, body = _http(method, base + path, payload, token)
            bodies.append(body)
        blob = json.dumps(bodies).lower()
        self.assertIsNone(re.search(
            r"(password_hash|salt_hex|password|secret|api_key|session_cookie"
            r"|private_key|credential)\s*[:=]\s*\S+", blob))
        self.assertNotIn("alice-secret-pw", blob)


class TestT19Shutdown(DeployedServerV2):
    def test_shutdown_clean(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        proc, base = self.launch(tmp.name)
        status, _ = _http("GET", base + "/health")
        self.assertEqual(status, 200)
        code = self.shutdown(proc)
        self.assertIsNotNone(code)
        with self.assertRaises(OSError):
            _http("GET", base + "/health")


class TestT20Restart(DeployedServerV2):
    def test_restart_same_store(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        tokens = self.prepare(tmp.name)
        proc, base = self.launch(tmp.name)
        try:
            status, created = _http("POST", base + "/workspaces/ws-a/tasks",
                                    {"title": "Survive restart"},
                                    token=tokens["alice"])
            self.assertEqual(status, 201)
            task_id = created["task_id"]
        finally:
            self.shutdown(proc)
        proc2, base2 = self.launch(tmp.name)
        try:
            status, body = _http("POST", base2 + "/users/login",
                                 {"username": "alice",
                                  "password": "alice-secret-pw"})
            self.assertEqual(status, 200)
            status, fetched = _http(
                "GET", base2 + f"/workspaces/ws-a/tasks/{task_id}",
                token=body["token"])
            self.assertEqual(status, 200)
            self.assertEqual(fetched["title"], "Survive restart")
        finally:
            self.shutdown(proc2)


class TestT21SecondStartupIsV2(DeployedServerV2):
    def test_restart_resolves_to_v2(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.prepare(tmp.name)
        proc, base = self.launch(tmp.name)
        try:
            self.assertIn("vertical_slice.serve_v2", proc.args)
            status, body = _http("GET", base + "/health")
            self.assertEqual(status, 200)
            self.assertEqual(body, {"status": "ok"})
        finally:
            self.shutdown(proc)
        proc2, base2 = self.launch(tmp.name)
        try:
            self.assertIn("vertical_slice.serve_v2", proc2.args)
            status, _ = _http("GET", base2 + "/health")
            self.assertEqual(status, 200)
        finally:
            self.shutdown(proc2)


class TestT22NormalizationDeterministic(DeployedServerV2):
    def test_normalized_description_stable(self):
        from vertical_slice import deployment_v2 as DEP
        first = DEP.normalize_contract(DEP.build_contract())
        second = DEP.normalize_contract(DEP.build_contract())
        self.assertEqual(first, second)
        blob = json.dumps(first).lower()
        for token in ("pid", "process_id", "bound_port", "timestamp"):
            self.assertNotIn(f'"{token}"', blob, token)


class TestT23UpstreamUnchanged(DeployedServerV2):
    def test_frozen_identities_recompute(self):
        from vertical_slice import deployment_v2 as DEP
        identities = DEP.verify_upstream()
        self.assertEqual(identities["d15_implementation_hash"],
                         EXPECTED_IMPL_HASH)
        self.assertEqual(identities["d14_selection_hash"],
                         EXPECTED_SELECTION_HASH)
        self.assertEqual(identities["d02_isr"], EXPECTED_ISR)


class TestT24NoEvolutionAuthorization(DeployedServerV2):
    def test_deployment_creates_no_authorization(self):
        from vertical_slice import deployment_v2 as DEP
        contract = DEP.build_contract()
        self.assertEqual(contract["authorization_mode"], "SYNTHETIC_TEST_ONLY")
        self.assertIs(contract["production_authorization"], False)
        self.assertEqual(contract["real_decision"], "NO_CHANGE")
        with open("vertical_slice/evolution_decision_v2_evidence.json",
                  encoding="utf-8") as f:
            self.assertEqual(json.load(f).get("decision"), "NO_CHANGE")


class TestT25ISRUnmutated(DeployedServerV2):
    def test_isr_still_resolves(self):
        from vertical_slice import implementation as IMPL
        from vertical_slice import regeneration as REG
        self.assertEqual(IMPL.frozen_input_identity()["vs-d02-isr-content-hash"],
                         EXPECTED_ISR)
        self.assertEqual(REG.validate_lineage(),
                         {"unresolved_isr": [], "unresolved_req": []})


class TestT26D13Unmutated(DeployedServerV2):
    def test_candidate_set_intact(self):
        with open("vertical_slice/evolution_evidence.json",
                  encoding="utf-8") as f:
            record = json.load(f)
        self.assertEqual(len(record.get("candidates", [])), 3)
        self.assertEqual(
            record["ordering"]["ranked_candidate_ids"][0], EXPECTED_ARCH)


class TestT27D14Unmutated(DeployedServerV2):
    def test_selection_record_intact(self):
        from vertical_slice import regeneration as REG
        selection = REG.load_selection()
        self.assertEqual(selection["selected_candidate_id"], EXPECTED_ARCH)
        self.assertEqual(selection["selected_candidate_hash"], EXPECTED_ARCH_HASH)
        self.assertEqual(selection["selection_hash"], EXPECTED_SELECTION_HASH)


class TestT28D15Unmutated(DeployedServerV2):
    def test_implementation_record_intact(self):
        from vertical_slice import regeneration as REG
        evidence = REG.build_evidence()
        self.assertEqual(evidence["implementation_hash"], EXPECTED_IMPL_HASH)
        self.assertEqual(len(evidence["component_mappings"]), 34)
        self.assertEqual(len(evidence["requirement_coverage"]), 13)


class TestT29NoOrphanProcess(DeployedServerV2):
    def test_all_launched_processes_terminated(self):
        orphans = [proc for proc in self._LAUNCHED if proc.poll() is None]
        self.assertEqual(orphans, [], f"{len(orphans)} orphan v2 process(es)")


class TestT30EvidenceProvenance(DeployedServerV2):
    def test_evidence_complete(self):
        from vertical_slice import deployment_v2 as DEP
        with open("vertical_slice/deployment_v2_evidence.json",
                  encoding="utf-8") as f:
            evidence = json.load(f)
        for section in DEP.EVIDENCE_SECTIONS:
            self.assertIn(section, evidence, section)
        provenance = evidence["provenance"]
        for field in DEP.PROVENANCE_FIELDS:
            self.assertIn(field, provenance, field)
        self.assertEqual(provenance["deployment_id"], "vs1-deploy-v2")
        self.assertEqual(provenance["implementation_id"], "vs1-impl-v2")
        self.assertEqual(provenance["implementation_hash"], EXPECTED_IMPL_HASH)
        self.assertEqual(provenance["architecture_id"], EXPECTED_ARCH)
        self.assertEqual(provenance["architecture_hash"], EXPECTED_ARCH_HASH)
        self.assertEqual(provenance["selection_hash"], EXPECTED_SELECTION_HASH)
        self.assertEqual(provenance["isr_hash"], EXPECTED_ISR)
        self.assertEqual(provenance["deployment_target"],
                         "local-uvicorn-loopback")
        self.assertIn("normalized_hash", evidence)


class TestT31SyntheticFirewall(DeployedServerV2):
    def test_synthetic_never_becomes_production(self):
        import os
        from vertical_slice import deployment_v2 as DEP
        self.assertEqual(DEP.AUTHORIZATION_MODE, "SYNTHETIC_TEST_ONLY")
        self.assertIs(DEP.PRODUCTION_AUTHORIZATION, False)
        for rel in (os.path.join("vertical_slice", "deployment_v2.py"),
                    os.path.join("vertical_slice", "serve_v2.py")):
            tree = ast.parse(open(rel, encoding="utf-8").read())
            for node in ast.walk(tree):
                if isinstance(node, ast.Assign):
                    targets = [t.id for t in node.targets
                               if isinstance(t, ast.Name)]
                    if "production_authorization" in [t.lower() for t in targets]:
                        self.assertIsInstance(node.value, ast.Constant, (rel, targets))
                        self.assertIs(node.value.value, False, (rel, targets))
        blob = json.dumps(DEP.build_contract())
        self.assertNotIn("PRODUCTION", blob)
        self.assertIn("SYNTHETIC_TEST_ONLY", blob)


if __name__ == "__main__":
    unittest.main()
