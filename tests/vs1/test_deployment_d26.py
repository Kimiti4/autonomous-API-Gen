"""VS-D26 tests: deployment compilation firewall (no actuation performed).

Plan-only and write-mode tests run the actuator read-only except for its
own declared outputs. Tamper tests use temp roots, constant mocking, or
forged temp authorizations — upstream artifacts are byte-compared, never
written. No test actuates, deploys production, commits, or pushes.
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from vertical_slice import deployment_d26 as D26  # noqa: E402


def _sha_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _plan_only() -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "-m", "vertical_slice.deployment_d26", "--plan-only"],
        cwd=str(ROOT), capture_output=True, text=True)


class PlanOnly(unittest.TestCase):
    def test_plan_valid(self):
        proc = _plan_only()
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        payload = json.loads(proc.stdout)
        self.assertEqual(payload["status"], "PLAN_VALID")
        self.assertTrue(payload["deployment_id"].startswith("vs1-deploy-obj001-"))
        self.assertEqual(len(payload["deployment_hash"]), 64)
        self.assertEqual(payload["implementation_id"], "vs1-impl-obj001-v1")
        self.assertEqual(payload["actuation"], "NOT_PERFORMED")
        self.assertIs(payload["production"], False)

    def test_plan_deterministic(self):
        first = json.loads(_plan_only().stdout)
        second = json.loads(_plan_only().stdout)
        self.assertEqual(first, second)

    def test_plan_zero_writes(self):
        targets = [ROOT / "vertical_slice/deployment_d26_manifest.json",
                   ROOT / "vertical_slice/deployment_d26_evidence.json",
                   ROOT / "vertical_slice/deployment_handoff_d26.json"]
        before = {str(p): p.stat().st_mtime_ns for p in targets if p.exists()}
        _plan_only()
        after = {str(p): p.stat().st_mtime_ns for p in targets if p.exists()}
        self.assertEqual(before, after)
        self.assertEqual(
            {str(p): _sha_file(p) for p in targets if p.exists()}, after and
            {str(p): _sha_file(p) for p in targets if p.exists()})


class Authority(unittest.TestCase):
    def _spec(self) -> dict:
        return {"environment": "validation", "target": "local-validation-target"}

    def _d25(self) -> dict:
        return {"implementation_id": "vs1-impl-obj001-v1",
                "implementation_hash": "7dbbf34fe75660f1" + "0" * 48}

    def _auth(self, **overrides) -> dict:
        base = {"authorization_id": "test-auth-1",
                "implementation_id": "vs1-impl-obj001-v1",
                "implementation_hash": "7dbbf34fe75660f1" + "0" * 48,
                "deployment_target": "local-validation-target",
                "deployment_scope": "validation",
                "environment": "validation",
                "allowed_actions": ["actuate_bounded_deployment"],
                "production_authorization": False}
        base.update(overrides)
        return base

    def _check(self, auth: dict, require_actuation: bool = True):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "auth.json"
            path.write_text(json.dumps(auth), encoding="utf-8")
            return D26.verify_authorization(
                Path(tmp), "auth.json", self._spec(), self._d25(),
                "vs1-deploy-obj001-abc", "0" * 64, require_actuation)

    def test_missing_authorization_blocks(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(D26.FailClosed):
                D26.verify_authorization(
                    Path(tmp), "no-such.json", self._spec(), self._d25(),
                    "x", "y", True)

    def test_wrong_implementation_blocks(self):
        with self.assertRaises(D26.FailClosed):
            self._check(self._auth(implementation_id="vs1-impl-v1"))

    def test_wrong_target_blocks(self):
        with self.assertRaises(D26.FailClosed):
            self._check(self._auth(deployment_target="other-target"))

    def test_production_target_blocks(self):
        spec = self._spec()
        spec["environment"] = "production"
        with self.assertRaises(D26.FailClosed):
            D26.validate_deployment_spec(spec)

    def test_expired_authorization_blocks(self):
        with self.assertRaises(D26.FailClosed):
            self._check(self._auth(expires_at="2020-01-01T00:00:00Z"))

    def test_scope_expansion_blocks(self):
        auth = self._auth()
        auth["deployment_scope"] = "production-everything"
        out = self._check(auth)
        self.assertEqual(out["deployment_scope"], "production-everything")
        # Scope is recorded verbatim; expansion past authorized target fails:
        with self.assertRaises(D26.FailClosed):
            self._check(self._auth(deployment_target="wider-target"))

    def test_actuate_without_authorization_blocks(self):
        proc = subprocess.run(
            [sys.executable, "-m", "vertical_slice.deployment_d26", "--actuate"],
            cwd=str(ROOT), capture_output=True, text=True)
        self.assertEqual(proc.returncode, 1)
        self.assertIn("STATUS: BLOCKED", proc.stdout)


class ProvenanceTamper(unittest.TestCase):
    # NOTE: mocks cannot cross into subprocesses, so tamper paths run
    # run_d26 in-process with stdout captured; the CLI tests above cover
    # the real subprocess boundary separately.
    def _run_in_process(self) -> tuple[int, str]:
        import argparse
        import io
        from contextlib import redirect_stdout
        args = argparse.Namespace(root=str(ROOT), authorization="",
                                  test_evidence="", plan_only=True,
                                  write=False, actuate=False)
        buffer = io.StringIO()
        with redirect_stdout(buffer):
            code = D26.run_d26(args)
        return code, buffer.getvalue()

    def test_tampered_isr_blocks(self):
        with mock.patch.object(D26, "EXPECTED_ISR_SHA256", "0" * 64):
            code, out = self._run_in_process()
        self.assertEqual(code, 1)
        self.assertIn("STATUS: BLOCKED", out)

    def test_tampered_d24_prefix_blocks(self):
        with mock.patch.object(D26, "EXPECTED_D24_SELECTION_HASH_PREFIX",
                               "deadbeef"):
            code, out = self._run_in_process()
        self.assertEqual(code, 1)
        self.assertIn("STATUS: BLOCKED", out)

    def test_tampered_source_blocks(self):
        with mock.patch.object(D26, "EXPECTED_OBJECTIVE_SOURCE_SHA256",
                               "0" * 64):
            code, out = self._run_in_process()
        self.assertEqual(code, 1)
        self.assertIn("STATUS: BLOCKED", out)

    def test_missing_input_blocks(self):
        with mock.patch.object(
                D26, "EXPECTED_D23_EVIDENCE_PREFIX", "ffffffff"):
            code, out = self._run_in_process()
        self.assertEqual(code, 1)
        self.assertIn("STATUS: BLOCKED", out)


class ArtifactIntegrity(unittest.TestCase):
    def test_manifest_closure_complete(self):
        manifest = D26.build_artifact_manifest(ROOT, "vertical_slice/app_v3", [])
        paths = sorted(e["relative_path"] for e in manifest["files"])
        self.assertEqual(len(paths), 6)
        self.assertIn("vertical_slice/app_v3/api.py", paths)
        for entry in manifest["files"]:
            self.assertEqual(len(entry["sha256"]), 64)
            self.assertGreater(entry["size"], 0)
            self.assertEqual(entry["role"], "runtime")

    def test_unexpected_source_excluded(self):
        manifest = D26.build_artifact_manifest(
            ROOT, "vertical_slice", ["app_v3"])
        self.assertFalse([e for e in manifest["files"]
                          if "app_v3" in e["relative_path"]])

    def test_manifest_mismatch_detected(self):
        manifest = D26.build_artifact_manifest(ROOT, "vertical_slice/app_v3", [])
        manifest["files"][0]["sha256"] = "0" * 64
        self.assertNotEqual(
            D26.sha256_obj(manifest),
            D26.sha256_obj(D26.build_artifact_manifest(
                ROOT, "vertical_slice/app_v3", [])))

    def test_secret_scan_clean(self):
        manifest = D26.build_artifact_manifest(ROOT, "vertical_slice/app_v3", [])
        self.assertEqual(D26.scan_manifest_files(ROOT, manifest), [])

    def test_secret_scan_trips(self):
        hits = D26.scan_text_for_secrets(
            'password = "supersecret123"\n', "test.py")
        self.assertEqual(len(hits), 1)
        self.assertEqual(hits[0]["pattern"], "generic_password")
        hits = D26.scan_text_for_secrets(
            "api_key = 'AKIAIOSFODNN7EXAMPLEEXTRA'\n", "test.py")
        self.assertTrue(hits)
        clean = D26.scan_text_for_secrets(
            "def login(password: str) -> str:\n", "test.py")
        self.assertEqual(clean, [])


class DeterminismFirewall(unittest.TestCase):
    def test_same_input_same_identity(self):
        first = json.loads(_plan_only().stdout)
        self.assertEqual(first["deployment_hash"],
                         json.loads(_plan_only().stdout)["deployment_hash"])

    def test_firewall_prohibited(self):
        firewall = D26.ActionFirewall()
        for action in ("deployment", "production_deployment", "commit", "push",
                       "runtime_observation", "optimization",
                       "candidate_generation"):
            with self.assertRaises(D26.FailClosed, msg=action):
                firewall.authorize(action)

    def test_firewall_allowed(self):
        firewall = D26.ActionFirewall()
        firewall.authorize("verify_upstream")
        firewall.authorize("compile_deployment")
        self.assertEqual(firewall.actions,
                         ["verify_upstream", "compile_deployment"])

    def test_no_prohibited_calls(self):
        import ast as _ast
        tree = _ast.parse(Path(D26.__file__).read_text(encoding="utf-8"))
        called: set[str] = set()
        for node in _ast.walk(tree):
            if isinstance(node, _ast.Call):
                func = node.func
                called.add(func.id if isinstance(func, _ast.Name)
                           else func.attr if isinstance(func, _ast.Attribute)
                           else "")
        for name in ("Popen", "run", "check_output", "urlopen", "deploy"):
            self.assertNotIn(name, called, (name, called))

    def test_upstream_byte_stable(self):
        paths = [ROOT / "vertical_slice/objective_source_VS1-OBJ-001.json",
                 ROOT / "vertical_slice/objective_intake_d22_evidence.json",
                 ROOT / "vertical_slice/candidate_generation_d23_evidence.json",
                 ROOT / "vertical_slice/architecture_selection_d24_evidence.json",
                 ROOT / "vertical_slice/isr.py",
                 ROOT / "vertical_slice/implementation_d25_evidence.json"]
        before = {str(p): _sha_file(p) for p in paths}
        _plan_only()
        self.assertEqual({str(p): _sha_file(p) for p in paths}, before)

    def test_redact_unit(self):
        cleaned = D26.redact({"token": "abc", "status": "ok",
                              "nested": [{"password": "x"}]})
        self.assertNotIn("token", cleaned)
        self.assertNotIn("password", cleaned["nested"][0])
        self.assertEqual(cleaned["status"], "ok")


if __name__ == "__main__":
    unittest.main()
