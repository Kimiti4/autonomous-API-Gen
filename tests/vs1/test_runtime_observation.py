"""VS-D17 tests T01-T30: runtime observation of the D16 v2 deployment.

Mechanical evidence only: no interpretation, authorization, mutation, or
evolution. Live tests run the observed API exclusively; process lifecycle
is owned by the test harness, never by the observation module.
"""
from __future__ import annotations

import ast
import json
import os
import tempfile
import unittest

from tests.vs1.test_deployment_v2 import DeployedServerV2, _http
from vertical_slice import runtime_observation as OBS

EXPECTED_GRAPH = (
    "28548494e754e9b8214e9f72511a7ba0187fa3378264306a82ff8868bd2e5526"
)
EXPECTED_ISR = "48e53dcef47aad84e52e20ec116f5b1f9616a626f42d1c281e3cc26cdf8e9dfb"
EXPECTED_ARCH = "vs1-evolved-96fe2d29fd76"
EXPECTED_ARCH_HASH = (
    "d0f8d7579a08de83e9490f373e6f1df70d44a546a1a8385cd27444516f724631"
)
EXPECTED_IMPL_HASH = (
    "d2090df69127e9922494bb7a4d526de087fd948ee793bdf326d5fe18fac1dd8c"
)
EXPECTED_D16_CONTRACT_HASH = "279fd4da7a47672cac211faf4da934208b9d2f66d8ed5d695fd7f4f7aa8f1dee"


def _seed(store_dir: str) -> str:
    from vertical_slice.app.models import Membership
    from vertical_slice.app_v2.service import TaskTrackerServiceV2
    from vertical_slice.app.store import TaskTrackerStore

    store = TaskTrackerStore(store_dir)
    service = TaskTrackerServiceV2(store)
    store.ensure_workspace("ws-obs", "Observed")
    admin = service.register("setup-admin", "a" * 16)
    store.put_membership(Membership("ws-obs", admin.user_id, "admin"))
    return service.login("setup-admin", "a" * 16)


def _transport(base: str):
    def call(method: str, url: str, body: object = None,
             token: str | None = None) -> tuple[int, object]:
        return _http(method, url, body, token)
    return call


class StaticIdentities(unittest.TestCase):
    def test_t01_d01(self):
        self.assertEqual(OBS.DEP.GRAPH_HASH, EXPECTED_GRAPH)

    def test_t02_d02(self):
        self.assertEqual(OBS.DEP.ISR_HASH, EXPECTED_ISR)

    def test_t03_d14(self):
        self.assertEqual(OBS.DEP.ARCHITECTURE_ID, EXPECTED_ARCH)
        self.assertEqual(OBS.DEP.ARCHITECTURE_HASH, EXPECTED_ARCH_HASH)
        self.assertEqual(OBS.DEP.SELECTION_HASH,
                         "f39c508e3a6ed52dbdd1b57766706804277e4cf70d12509f71f589370f549d1b")

    def test_t04_d15(self):
        from vertical_slice import regeneration as REG
        self.assertEqual(REG.build_evidence()["implementation_hash"],
                         EXPECTED_IMPL_HASH)

    def test_t05_d16(self):
        from vertical_slice import deployment_v2 as DEP
        self.assertEqual(DEP.contract_hash(), EXPECTED_D16_CONTRACT_HASH)
        with open("vertical_slice/deployment_v2_evidence.json",
                  encoding="utf-8") as f:
            evidence = json.load(f)
        self.assertEqual(evidence["provenance"]["deployment_id"],
                         "vs1-deploy-v2")


class ObservedWorkload(DeployedServerV2):
    EXECUTION_ID = "vs1-d17-test-run"

    @classmethod
    def setUpClass(cls):
        cls._tmp = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls._tmp.cleanup)
        cls._store_dir = cls._tmp.name
        cls._admin = _seed(cls._tmp.name)
        cls._proc, cls._base = cls.launch(cls._tmp.name)
        cls.addClassCleanup(lambda: cls.shutdown(cls._proc))
        cls._records = OBS.run_online_workload(
            cls._base, cls.EXECUTION_ID, _transport(cls._base), cls._admin)
        cls._by_id = {r["observation_id"]: r for r in cls._records}

    def test_t06_v2_deployment_identity(self):
        identity = OBS.verify_deployment_identity()
        self.assertEqual(identity["deployment_id"], "vs1-deploy-v2")
        self.assertEqual(identity["implementation_id"], "vs1-impl-v2")
        self.assertEqual(identity["implementation_hash"], EXPECTED_IMPL_HASH)
        self.assertEqual(identity["architecture_id"], EXPECTED_ARCH)
        self.assertEqual(identity["isr_hash"], EXPECTED_ISR)
        self.assertIn("vertical_slice.serve_v2", self._proc.args)

    def test_t07_v1_rejection(self):
        self.assertNotIn("vertical_slice.serve", self._proc.args)
        self.assertEqual(OBS.DEP.IMPLEMENTATION_ID, "vs1-impl-v2")
        self.assertNotEqual(OBS.DEP.IMPLEMENTATION_ID, "vs1-impl-v1")

    def _assert_pass(self, observation_id: str, expected_class: str):
        record = self._by_id[observation_id]
        self.assertEqual(record["observed_class"], expected_class,
                         observation_id)
        self.assertEqual(record["status"], "PASS", observation_id)

    def test_t08_registration(self):
        self._assert_pass("auth.register", "http-201")

    def test_t09_login(self):
        self._assert_pass("auth.login", "http-200")

    def test_t10_invalid_credential(self):
        self._assert_pass("auth.invalid-rejected", "http-401")

    def test_t11_authorization(self):
        self._assert_pass("authz.admin-grant", "http-201")
        self._assert_pass("auth.authenticated-request", "http-200")
        self._assert_pass("authz.permitted-operation", "http-201")

    def test_t12_outsider(self):
        self._assert_pass("authz.outsider-rejected", "http-403")
        self._assert_pass("authz.role-rejected", "http-403")

    def test_t13_crud(self):
        for obs_id, expected in (("crud.create", "http-201"),
                                 ("crud.read", "http-200"),
                                 ("crud.update", "http-200"),
                                 ("crud.read-after-update", "http-200"),
                                 ("crud.delete", "http-204"),
                                 ("crud.read-after-delete", "http-422")):
            self._assert_pass(obs_id, expected)

    def test_t18_latency_measured(self):
        for obs_id in ("lifecycle.readiness", "crud.read"):
            measurement = self._by_id[obs_id]["measurement"]
            self.assertIn("latency_ms", measurement, obs_id)
            self.assertIsInstance(measurement["latency_ms"], float, obs_id)
            self.assertGreaterEqual(measurement["latency_ms"], 0.0, obs_id)

    def test_t20_secret_redaction(self):
        for record in self._records:
            OBS.assert_secret_safe(record)  # raises on any secret shape


class LifecycleObservation(DeployedServerV2):
    @classmethod
    def setUpClass(cls):
        cls._tmp = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls._tmp.cleanup)
        cls._store_dir = cls._tmp.name
        cls._admin = _seed(cls._tmp.name)

    @classmethod
    def _ensure_sequence(cls):
        if hasattr(cls, "_sequence"):
            return cls._sequence
        execution_id = "vs1-d17-test-lifecycle"
        proc, base = cls.launch(cls._store_dir)
        try:
            records = OBS.run_online_workload(
                base, execution_id, _transport(base), cls._admin)
            status, _ = _http(
                "POST", base + "/workspaces/ws-obs/tasks",
                {"title": "Persist probe"}, token=cls._admin)
            assert status == 201
        finally:
            code1 = cls.shutdown(proc)
        proc2, base2 = cls.launch(cls._store_dir)
        try:
            status, body = _http("POST", base2 + "/users/login",
                                 {"username": "setup-admin",
                                  "password": "a" * 16})
            assert status == 200
            status, tasks = _http("GET", base2 + "/workspaces/ws-obs/tasks",
                                  token=body["token"])
            titles = [t["title"] for t in tasks]
            records.append(OBS.observe(
                observation_id="persist.restart-state",
                execution_id=execution_id,
                operation="lifecycle.restart-persist",
                expected_class="state-preserved",
                observed_class=("state-preserved"
                                if "Persist probe" in titles
                                else "state-divergent"),
                status=("PASS" if "Persist probe" in titles else "FAIL"),
                measurement={"http_status": status,
                             "task_count": len(tasks)}))
        finally:
            code2 = cls.shutdown(proc2)
        try:
            _http("GET", base2 + "/health")
            post = "reachable"
        except OSError:
            post = "refused"
        records.append(OBS.observe(
            observation_id="lifecycle.shutdown-clean",
            execution_id=execution_id, operation="lifecycle.shutdown",
            expected_class="shutdown-clean",
            observed_class=("shutdown-clean"
                            if (code1, code2, post) != (None, None, "reachable")
                            and code1 is not None and code2 is not None
                            and post == "refused"
                            else "shutdown-anomalous"),
            status=("PASS" if code1 is not None and code2 is not None
                    and post == "refused" else "FAIL"),
            measurement={"clean_shutdowns": sum(
                1 for c in (code1, code2) if c is not None)}))
        cls._sequence = records
        return records

    def _record(self, observation_id: str) -> dict[str, object]:
        by_id = {r["observation_id"]: r for r in self._ensure_sequence()}
        return by_id[observation_id]

    def test_t14_persistence(self):
        record = self._record("persist.restart-state")
        self.assertEqual(record["observed_class"], "state-preserved")
        self.assertEqual(record["status"], "PASS")

    def test_t15_restart(self):
        # Restart is the mechanism behind persist.restart-state: the record
        # exists only because the second launch served the same store.
        record = self._record("persist.restart-state")
        self.assertEqual(record["operation"], "lifecycle.restart-persist")
        self.assertEqual(record["status"], "PASS")

    def test_t17_shutdown(self):
        record = self._record("lifecycle.shutdown-clean")
        self.assertEqual(record["observed_class"], "shutdown-clean")
        self.assertEqual(record["status"], "PASS")

    def test_t16_events(self):
        with open(os.path.join(self._store_dir, "store.json"),
                  encoding="utf-8") as f:
            state = json.load(f)
        created = [e for e in state["events"]
                   if e["event_name"] == "task-created"]
        self.assertTrue(created)
        self.assertTrue(all(e["producer"] == "svc-task" for e in created))
        self.assertTrue(all(e["task_id"] for e in created))


class ObservationMechanics(unittest.TestCase):
    def _provenance(self) -> dict[str, str]:
        return OBS.provenance_block("vs1-d17-unit")

    def _record(self, **overrides) -> dict[str, object]:
        base: dict[str, object] = {
            "observation_id": "unit.probe",
            "execution_id": "vs1-d17-unit",
            "deployment_id": "vs1-deploy-v2",
            "implementation_id": "vs1-impl-v2",
            "architecture_id": EXPECTED_ARCH,
            "operation": "http.probe",
            "expected_class": "http-200",
            "observed_class": "http-200",
            "status": "PASS",
            "measurement": {"http_status": 200, "latency_ms": 1.5},
            "timestamp": "2026-01-01T00:00:00Z",
            "provenance": self._provenance(),
        }
        base.update(overrides)
        return base

    def test_t19_failure_classification(self):
        undetermined = OBS.validate_record(self._record(
            observed_class=None, status="UNDETERMINED"))
        self.assertEqual(undetermined["status"], "UNDETERMINED")
        blocked = OBS.validate_record(self._record(
            observed_class=None, status="BLOCKED"))
        self.assertEqual(blocked["status"], "BLOCKED")
        with self.assertRaises(OBS.ObservationError):
            OBS.validate_record(self._record(
                observed_class=None, status="PASS"))

    def test_t21_provenance(self):
        record = OBS.validate_record(self._record())
        chain = [record["provenance"][field] for field in
                 ("execution_id", "deployment_id", "implementation_id",
                  "architecture_id", "isr_hash")]
        self.assertTrue(all(chain))
        self.assertEqual(record["provenance"]["isr_hash"], EXPECTED_ISR)

    def test_t22_schema(self):
        OBS.validate_record(self._record())
        broken = self._record()
        del broken["measurement"]
        with self.assertRaises(OBS.ObservationError):
            OBS.validate_record(broken)

    def test_t23_normalization(self):
        first = OBS.normalize_record(self._record())
        # Same semantic content, different runtime-variable values: the
        # presence flags (not the values) participate in equivalence.
        second = OBS.normalize_record(self._record(
            timestamp="2027-05-05T00:00:00Z",
            measurement={"http_status": 200, "latency_ms": 99.9}))
        self.assertEqual(first, second)
        self.assertNotIn("timestamp", first)
        self.assertNotIn("latency_ms", first["measurement"])
        self.assertTrue(first["measurement"]["latency_ms_measured"])

    def test_t26_fail_closed_identity(self):
        broken = self._record()
        broken["provenance"] = dict(self._provenance())
        del broken["provenance"]["isr_hash"]
        with self.assertRaises(OBS.ObservationError):
            OBS.validate_record(broken)

    def test_t27_fail_closed_malformed(self):
        with self.assertRaises(OBS.ObservationError):
            OBS.observe(observation_id="unit.bad",
                        execution_id="vs1-d17-unit", operation="http.probe",
                        expected_class="http-200", observed_class="http-200",
                        status="ALMOST")
        with self.assertRaises(OBS.ObservationError):
            OBS.validate_record({"observation_id": "unit.bad"})

    def test_t28_firewall(self):
        # NOTE: boundary words ("interpretation", "mutation", …) legitimately
        # appear in the module's own boundary docstrings, so this firewall
        # tests machinery (imports, calls, writes), not English vocabulary.
        import vertical_slice.runtime_observation as module
        src = open(module.__file__, encoding="utf-8").read()
        tree = ast.parse(src)
        imports: set[str] = set()
        called: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.update(a.name for a in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imports.add(node.module)
            elif isinstance(node, ast.Call):
                func = node.func
                if isinstance(func, ast.Name):
                    called.add(func.id)
                elif isinstance(func, ast.Attribute):
                    called.add(func.attr)
        # NOTE: `from vertical_slice import deployment_v2` parses as
        # module "vertical_slice" — read-only consumption of the D16
        # contract is the legitimate deployment-identity path.
        allowed = {"__future__", "hashlib", "json", "re", "time",
                   "typing", "urllib.error", "urllib.request",
                   "vertical_slice"}
        self.assertLessEqual(imports, allowed, imports)
        for name in ("choose_candidate", "decide", "retire", "mutate",
                     "crossover", "optimize", "regenerate", "redeploy",
                     "interpret", "authorize", "promote"):
            self.assertNotIn(name, called, (name, called))
        for guard in ("vertical_slice/isr.py", "vertical_slice/candidates.py",
                      "vertical_slice/regeneration.py",
                      "vertical_slice/deployment_v2.py",
                      "vertical_slice/serve_v2.py",
                      "release/evidence", "certification/"):
            self.assertNotIn(guard, src, guard)

    def test_t29_upstream_immutable(self):
        from vertical_slice import deployment_v2 as DEP
        from vertical_slice import regeneration as REG
        self.assertEqual(REG.build_evidence()["implementation_hash"],
                         EXPECTED_IMPL_HASH)
        self.assertEqual(DEP.contract_hash(), EXPECTED_D16_CONTRACT_HASH)
        self.assertEqual(REG.load_selection()["selection_hash"],
                         "f39c508e3a6ed52dbdd1b57766706804277e4cf70d12509f71f589370f549d1b")

    def test_t30_no_evolution_side_effect(self):
        import vertical_slice.runtime_observation as module
        tree = ast.parse(open(module.__file__, encoding="utf-8").read())
        called = {node.func.id for node in ast.walk(tree)
                  if isinstance(node, ast.Call)
                  and isinstance(node.func, ast.Name)}
        for name in ("choose_candidate", "build_evidence", "run_gate"):
            self.assertNotIn(name, called, (name, called))
        evidence = json.load(open("vertical_slice/runtime_observation_evidence.json",
                                  encoding="utf-8"))
        self.assertIs(evidence["production_authorization"], False)
        self.assertEqual(evidence["authorization_mode"], "SYNTHETIC_TEST_ONLY")
        self.assertNotIn("verdict", json.dumps(evidence).lower())


class RepeatedRunEquivalence(DeployedServerV2):
    def _single_run(self) -> list[dict[str, object]]:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        admin = _seed(tmp.name)
        proc, base = self.launch(tmp.name)
        try:
            return OBS.run_online_workload(
                base, "vs1-d17-repeat", _transport(base), admin)
        finally:
            self.shutdown(proc)

    def test_t24_repeated_run_equivalence(self):
        first = OBS.normalize_evidence(self._single_run())
        second = OBS.normalize_evidence(self._single_run())
        self.assertEqual(first, second)

    def test_t25_invariants(self):
        evidence = json.load(open("vertical_slice/runtime_observation_evidence.json",
                                  encoding="utf-8"))
        for section in ("constitutional_invariants", "security_invariants",
                        "behavioral_invariants"):
            self.assertTrue(all(status == "PASS"
                                for status in evidence[section].values()),
                            (section, evidence[section]))
        self.assertEqual(evidence["summary"]["status_counts"]["FAIL"], 0)


if __name__ == "__main__":
    unittest.main()
