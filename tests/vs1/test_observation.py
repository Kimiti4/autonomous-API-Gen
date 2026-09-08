"""VS-D06 tests T01-T22: bounded observation + evidence (facts only)."""
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


def _launch(store_dir: str) -> tuple[subprocess.Popen, str]:
    env = dict(os.environ, VS1_STORE_DIR=store_dir, VS1_PORT="0",
               PYTHONDONTWRITEBYTECODE="1")
    proc = subprocess.Popen(
        [sys.executable, "-m", "vertical_slice.serve"],
        env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        text=True, cwd=os.getcwd())
    assert proc.stdout is not None
    pattern = re.compile(r"Uvicorn running on http://127\.0\.0\.1:(\d+)")
    base, deadline = "", time.time() + 30
    while time.time() < deadline:
        line = proc.stdout.readline()
        if not line:
            break
        match = pattern.search(line)
        if match:
            base = f"http://127.0.0.1:{match.group(1)}"
            break
    if not base or proc.poll() is not None:
        proc.kill()
        raise AssertionError("observation target did not start")
    ready_by = time.time() + 20
    while time.time() < ready_by:
        try:
            with urllib.request.urlopen(base + "/health", timeout=5) as response:
                if response.status == 200:
                    return proc, base
        except OSError:
            pass
        time.sleep(0.2)
    proc.kill()
    raise AssertionError("readiness never satisfied")


def _shutdown(proc: subprocess.Popen) -> None:
    proc.terminate()
    try:
        proc.wait(timeout=15)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait(timeout=15)


def _prepare(store_dir: str) -> dict[str, str]:
    from vertical_slice.app.models import Membership
    from vertical_slice.app.service import TaskTrackerService
    from vertical_slice.app.store import TaskTrackerStore

    state = {"n": 0}

    def generate() -> str:
        state["n"] += 1
        return f"vs1-obs-token-{state['n']:04d}"

    store = TaskTrackerStore(store_dir)
    service = TaskTrackerService(store, token_generator=generate)
    store.ensure_workspace("ws-a", "Alpha")
    alice = service.register("alice", "alice-secret-pw")
    admin = service.register("cara-admin", "cara-secret-pw")
    store.put_membership(Membership("ws-a", alice.user_id, "member"))
    store.put_membership(Membership("ws-a", admin.user_id, "admin"))
    return {
        "alice": service.login("alice", "alice-secret-pw"),
        "admin": service.login("cara-admin", "cara-secret-pw"),
        "alice_id": alice.user_id,
    }


def _provenance() -> dict[str, str]:
    from vertical_slice import observation as OBS
    return {
        "observation_contract": OBS.OBSERVATION_CONTRACT_ID,
        "deployment_id": OBS.DEPLOYMENT_ID,
        "implementation_id": OBS.IMPLEMENTATION_ID,
        "vs-d01-graph-sha256": "28548494e754e9b8214e9f72511a7ba0187fa3378264306a82ff8868bd2e5526",
        "vs-d02-isr-content-hash": "48e53dcef47aad84e52e20ec116f5b1f9616a626f42d1c281e3cc26cdf8e9dfb",
        "vs-d03-selected": "vs1-candidate-a",
    }


class ObservedDeployment(unittest.TestCase):
    def run_observed(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self._last_dir = tmp.name
        tokens = _prepare(tmp.name)
        proc, base = _launch(tmp.name)
        self.addCleanup(lambda: _shutdown(proc))
        return base, tokens


class TestT01FrozenD01(ObservedDeployment):
    def test_d01_identity(self):
        from vertical_slice import observation as OBS
        identity = OBS.contract_identity()
        self.assertEqual(
            identity["vs-d01-graph-sha256"],
            "28548494e754e9b8214e9f72511a7ba0187fa3378264306a82ff8868bd2e5526")


class TestT02FrozenD02(ObservedDeployment):
    def test_d02_identity(self):
        from vertical_slice import observation as OBS
        identity = OBS.contract_identity()
        self.assertEqual(
            identity["vs-d02-isr-content-hash"],
            "48e53dcef47aad84e52e20ec116f5b1f9616a626f42d1c281e3cc26cdf8e9dfb")


class TestT03FrozenD03(ObservedDeployment):
    def test_d03_selection(self):
        from vertical_slice import observation as OBS
        identity = OBS.contract_identity()
        self.assertEqual(identity["vs-d03-selected"], "vs1-candidate-a")


class TestT04FrozenD04(ObservedDeployment):
    def test_d04_implementation(self):
        from vertical_slice import implementation as IMPL
        self.assertEqual(IMPL.IMPLEMENTATION_VERSION, "vs1-impl-v1")
        self.assertEqual(IMPL.build_evidence()["candidate_id"], "vs1-candidate-a")


class TestT05FrozenD05(ObservedDeployment):
    def test_d05_deployment(self):
        from vertical_slice.deployment import (
            CANDIDATE_ID,
            DEPLOYMENT_CONTRACT_VERSION,
            build_contract,
        )
        self.assertEqual(CANDIDATE_ID, "vs1-candidate-a")
        self.assertEqual(DEPLOYMENT_CONTRACT_VERSION, "vs1-deploy-v1")
        self.assertEqual(build_contract()["candidate_id"], "vs1-candidate-a")


class TestT06ContractIdentity(ObservedDeployment):
    def test_contract_identity(self):
        from vertical_slice import observation as OBS
        self.assertEqual(OBS.OBSERVATION_CONTRACT_ID, "vs1-observe-v1")
        self.assertEqual(OBS.OBSERVATION_CONTRACT_VERSION, "vs1-observe-v1")
        self.assertEqual(len(OBS.PROBES), 7)
        self.assertEqual(
            {p["probe_id"] for p in OBS.PROBES},
            {"P01-readiness", "P02-authentication", "P03-crud-lifecycle",
             "P04-authorization", "P05-persistence", "P06-events", "P07-lifecycle"})


class TestT07Readiness(ObservedDeployment):
    def test_readiness_observation(self):
        from vertical_slice import observation as OBS
        base, tokens = self.run_observed()
        records = OBS.collect(base, tokens, self._last_dir, _provenance())
        by_probe = {r["probe_id"]: r for r in records}
        self.assertEqual(by_probe["P01-readiness"]["result"], "ready")
        self.assertEqual(by_probe["P01-readiness"]["status"], "observed")



class TestT08Authentication(ObservedDeployment):
    def test_authentication_observation(self):
        from vertical_slice import observation as OBS
        base, tokens = self.run_observed()
        records = OBS.collect(base, tokens, self._last_dir, _provenance())
        by_probe = {r["probe_id"]: r for r in records}
        self.assertEqual(by_probe["P02-authentication"]["result"], "rejected")
        blob = json.dumps(records).lower()
        self.assertNotIn("alice-secret", blob)
        self.assertNotIn("vs1-obs-token", blob)

    def _dir_of(self, _base: str) -> str:
        return self._last_dir

    def run_observed(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self._last_dir = tmp.name
        tokens = _prepare(tmp.name)
        proc, base = _launch(tmp.name)
        self.addCleanup(lambda: _shutdown(proc))
        self._base, self._tokens = base, tokens
        return base, tokens


class TestT09Crud(ObservedDeployment):
    def test_crud_observation(self):
        from vertical_slice import observation as OBS
        base, tokens = self.run_observed()
        records = OBS.collect(base, tokens, self._last_dir, _provenance())
        by_probe = {r["probe_id"]: r for r in records}
        self.assertEqual(by_probe["P03-crud-lifecycle"]["result"], "lifecycle-completed")



class TestT10Authorization(ObservedDeployment):
    def test_authorization_observation(self):
        from vertical_slice import observation as OBS
        base, tokens = self.run_observed()
        records = OBS.collect(base, tokens, self._last_dir, _provenance())
        by_probe = {r["probe_id"]: r for r in records}
        self.assertEqual(by_probe["P04-authorization"]["result"], "outsider-rejected")



class TestT11Persistence(ObservedDeployment):
    def test_persistence_observation(self):
        from vertical_slice import observation as OBS
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        tokens = _prepare(tmp.name)
        proc, base = _launch(tmp.name)
        try:
            def do_restart() -> str:
                _shutdown(proc)
                proc2, base2 = _launch(tmp.name)
                self.addCleanup(lambda: _shutdown(proc2))
                return base2
            records = OBS.collect(base, tokens, tmp.name, _provenance(),
                                  do_restart=do_restart)
        finally:
            if proc.poll() is None:
                _shutdown(proc)
        by_probe = {r["probe_id"]: r for r in records}
        self.assertEqual(by_probe["P05-persistence"]["result"], "survived-restart")


class TestT12Events(ObservedDeployment):
    def test_event_observation(self):
        from vertical_slice import observation as OBS
        base, tokens = self.run_observed()
        records = OBS.collect(base, tokens, self._last_dir, _provenance())
        by_probe = {r["probe_id"]: r for r in records}
        self.assertEqual(by_probe["P06-events"]["result"], "emitted")



class TestT13Lifecycle(ObservedDeployment):
    def test_lifecycle_observation(self):
        from vertical_slice import observation as OBS
        base, tokens = self.run_observed()
        records = OBS.collect(base, tokens, self._last_dir, _provenance())
        by_probe = {r["probe_id"]: r for r in records}
        self.assertEqual(by_probe["P07-lifecycle"]["result"], "running")



class TestT14Provenance(ObservedDeployment):
    def test_provenance_complete(self):
        from vertical_slice import observation as OBS
        base, tokens = self.run_observed()
        records = OBS.collect(base, tokens, self._last_dir, _provenance())
        for record in records:
            for field in ("observation_contract", "deployment_id",
                          "implementation_id", "vs-d01-graph-sha256",
                          "vs-d02-isr-content-hash", "vs-d03-selected"):
                self.assertIn(field, record["provenance"], (record["probe_id"], field))



class TestT15Redaction(ObservedDeployment):
    def test_no_secrets_recorded(self):
        from vertical_slice import observation as OBS
        base, tokens = self.run_observed()
        records = OBS.collect(base, tokens, self._last_dir, _provenance())
        blob = json.dumps(records).lower()
        for marker in ("alice-secret", "bob-secret", "cara-secret",
                       "vs1-obs-token", "password"):
            self.assertNotIn(marker, blob, marker)

    def test_scrub_on_entry(self):
        from vertical_slice import observation as OBS
        record = OBS.make_record(
            "P01-readiness", "readiness", "/health", "ready", "observed",
            {"token": "abc", "nested": {"password": "x"}}, 1, _provenance())
        blob = json.dumps(record)
        self.assertNotIn("abc", blob)
        self.assertIn("[redacted]", blob)



class TestT16Schema(ObservedDeployment):
    def test_missing_field_rejected(self):
        from vertical_slice import observation as OBS
        record = OBS.make_record(
            "P01-readiness", "readiness", "/health", "ready", "observed",
            {"http_status": 200}, 1, _provenance())
        broken = dict(record)
        del broken["status"]
        with self.assertRaises(OBS.ObservationError):
            OBS.validate_record(broken)

    def test_unknown_probe_rejected(self):
        from vertical_slice import observation as OBS
        with self.assertRaises(OBS.ObservationError):
            OBS.make_record("P99-evil", "x", "y", "z", "observed", {}, 1,
                            _provenance())


class TestT17Normalization(ObservedDeployment):
    def test_normalization_deterministic(self):
        from vertical_slice import observation as OBS
        first = OBS.normalize([
            OBS.make_record("P01-readiness", "readiness", "/health", "ready",
                            "observed", {"http_status": 200}, 2, _provenance()),
            OBS.make_record("P02-authentication", "authentication", "/users/login",
                            "rejected", "observed", {"http_status": 401}, 1,
                            _provenance()),
        ])
        second = OBS.normalize(list(reversed(first)))
        self.assertEqual(first, second)
        self.assertEqual([r["sequence"] for r in first], [1, 2])


class TestT18Equivalence(ObservedDeployment):
    def test_repeated_runs_equivalent(self):
        from vertical_slice import observation as OBS

        def one_run():
            tmp = tempfile.TemporaryDirectory()
            self.addCleanup(tmp.cleanup)
            tokens = _prepare(tmp.name)
            proc, base = _launch(tmp.name)
            try:
                return OBS.normalize(OBS.collect(base, tokens, tmp.name, _provenance()))
            finally:
                _shutdown(proc)

        # P05 without restart hook observes store presence; task ids are
        # deterministic counters from an empty store, so runs must match.
        self.assertEqual(one_run(), one_run())


class TestT19InvalidDeployment(ObservedDeployment):
    def test_dead_target_fails_closed(self):
        from vertical_slice import observation as OBS
        with self.assertRaises(Exception):
            OBS.collect("http://127.0.0.1:1", {}, tempfile.gettempdir(), _provenance())


class TestT20IncompleteProvenance(ObservedDeployment):
    def test_incomplete_provenance_rejected(self):
        from vertical_slice import observation as OBS
        broken = dict(_provenance())
        del broken["vs-d02-isr-content-hash"]
        with self.assertRaises(OBS.ObservationError):
            OBS.make_record("P01-readiness", "readiness", "/health", "ready",
                            "observed", {"http_status": 200}, 1, broken)


class TestT21Boundary(ObservedDeployment):
    def test_no_interpretation_evolution_work(self):
        import ast
        import os
        src = open(os.path.join("vertical_slice", "observation.py"),
                   encoding="utf-8").read()
        tree = ast.parse(src)
        imports: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.update(a.name.split(".")[0] for a in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imports.add(node.module.split(".")[0])
            self.assertLessEqual(
                imports,
                {"__future__", "typing", "urllib", "json", "os",
                 "vertical_slice"},
                imports)
            # Identifier-level check (docstrings/comments excluded): the
            # module documents its prohibitions in prose, so raw-substring
            # matching would false-positive. Code identifiers must not
            # reference interpretation/evolution machinery.
            identifiers: set[str] = set()
            for node in ast.walk(tree):
                if isinstance(node, ast.Name):
                    identifiers.add(node.id.lower())
                elif isinstance(node, ast.Attribute):
                    identifiers.add(node.attr.lower())
            for token in ("evolution", "compiler", "telemetry", "prometheus",
                          "opentelemetry", "optimize", "benchmark", "chaos",
                          "remediate", "interpret"):
                self.assertNotIn(token, identifiers, token)


class TestT22UpstreamImmutability(ObservedDeployment):
    def test_upstream_untouched_by_observation(self):
        from vertical_slice import implementation as IMPL
        from vertical_slice import candidates as C
        from vertical_slice.isr import build_task_tracker_isr
        from vertical_slice.requirements import build_task_tracker_requirements
        graph_before = build_task_tracker_requirements()
        rev_before = build_task_tracker_isr()
        from vertical_slice import observation as OBS
        OBS.contract_identity()
        self.assertEqual(build_task_tracker_requirements(), graph_before)
        self.assertEqual(build_task_tracker_isr(), rev_before)
        self.assertEqual(C.select_candidate()["selected"], "vs1-candidate-a")
        self.assertIn("vs1-candidate-a", IMPL.build_evidence()["candidate_id"])


if __name__ == "__main__":
    unittest.main()
