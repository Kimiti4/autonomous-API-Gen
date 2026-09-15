"""Actuator tests: plan-only determinism, emission stability, fail-closed
paths, firewall, redaction, overwrite guard. Live-chain tests invoke the
CLI read-only except for the actuator-owned manifest/handoff pair, whose
byte-stability is itself asserted.
"""
from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ACTUATOR = ROOT / "vertical_slice" / "d25_authority_actuator.py"
BEHAVIOR = ROOT / "vertical_slice" / "behavior_evidence_d25.json"
MANIFEST = ROOT / "vertical_slice" / "implementation_d25_manifest.json"
HANDOFF = ROOT / "vertical_slice" / "deployment_handoff_d25.json"


def _run(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(ACTUATOR), *args],
        cwd=str(ROOT), capture_output=True, text=True)


class PlanOnly(unittest.TestCase):
    def test_plan_only_passes(self):
        proc = _run("--plan-only")
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        payload = json.loads(proc.stdout)
        self.assertTrue(payload["implementation_id"].startswith("vs1-impl-obj001-"))
        self.assertEqual(len(payload["implementation_hash"]), 64)

    def test_plan_only_deterministic(self):
        first = json.loads(_run("--plan-only").stdout)
        second = json.loads(_run("--plan-only").stdout)
        self.assertEqual(first, second)

    def test_plan_only_writes_nothing(self):
        before = {p: p.stat().st_mtime_ns for p in (MANIFEST, HANDOFF)
                  if p.exists()}
        _run("--plan-only")
        after = {p: p.stat().st_mtime_ns for p in (MANIFEST, HANDOFF)
                 if p.exists()}
        self.assertEqual(before, after)


class Emission(unittest.TestCase):
    def test_write_passes(self):
        proc = _run("--behavior-evidence",
                    "vertical_slice/behavior_evidence_d25.json", "--write")
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        payload = json.loads(proc.stdout)
        self.assertEqual(payload["status"], "PASS")
        self.assertEqual(payload["behavior_checks"], "33/33")

    def test_emission_byte_stable(self):
        first_manifest = MANIFEST.read_bytes()
        first_handoff = HANDOFF.read_bytes()
        _run("--behavior-evidence",
             "vertical_slice/behavior_evidence_d25.json", "--write")
        self.assertEqual(MANIFEST.read_bytes(), first_manifest)
        self.assertEqual(HANDOFF.read_bytes(), first_handoff)

    def test_manifest_content(self):
        manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
        self.assertIn("plan", manifest)
        self.assertEqual(manifest["policy_version"], "d25-authority-v1")
        self.assertEqual(
            manifest["plan"]["authority_chain"]["candidate_id"],
            "vs1-obj001-candidate-313b071dd7d4")

    def test_handoff_content(self):
        handoff = json.loads(HANDOFF.read_text(encoding="utf-8"))
        self.assertIs(handoff["production_authorization"], False)
        self.assertIs(handoff["deployment_performed"], False)
        self.assertEqual(handoff["objective_id"], "VS1-OBJ-001")

    def test_no_secrets_emitted(self):
        blob = (MANIFEST.read_text(encoding="utf-8")
                + HANDOFF.read_text(encoding="utf-8")).lower()
        import re
        self.assertIsNone(re.search(
            r"(password|secret|api_key|session_cookie|private_key"
            r"|credential)\s*[:=]\s*\S+", blob))


class FailClosed(unittest.TestCase):
    def test_missing_behavior_blocked(self):
        proc = _run("--behavior-evidence", "vertical_slice/no-such.json")
        self.assertEqual(proc.returncode, 1)
        self.assertIn("STATUS: BLOCKED", proc.stdout)

    def test_no_behavior_no_plan_only_blocked(self):
        proc = _run()
        self.assertEqual(proc.returncode, 1)
        self.assertIn("STATUS: BLOCKED", proc.stdout)

    def test_tampered_check_blocked(self):
        import tempfile
        data = json.loads(BEHAVIOR.read_text(encoding="utf-8"))
        data["checks"]["t19_priority_filter_works"] = False
        with tempfile.NamedTemporaryFile(
                mode="w", suffix=".json", delete=False,
                dir=str(Path(__file__).resolve().parent)) as tmp:
            json.dump(data, tmp)
            name = tmp.name
        try:
            proc = _run("--behavior-evidence",
                        str(Path(name).relative_to(ROOT)))
            self.assertEqual(proc.returncode, 1)
            self.assertIn("t19_priority_filter_works", proc.stdout)
        finally:
            Path(name).unlink()

    def test_firewall_unit(self):
        sys.path.insert(0, str(ROOT / "vertical_slice"))
        import d25_authority_actuator as actuator
        firewall = actuator.ActionFirewall()
        firewall.authorize("verify_upstream")
        with self.assertRaises(actuator.FailClosed):
            firewall.authorize("deployment")
        with self.assertRaises(actuator.FailClosed):
            firewall.authorize("push")
        with self.assertRaises(actuator.FailClosed):
            firewall.authorize("invent_new_action")

    def test_redact_unit(self):
        sys.path.insert(0, str(ROOT / "vertical_slice"))
        import d25_authority_actuator as actuator
        cleaned = actuator.redact({"token": "abc", "status": "ok",
                                   "nested": [{"password": "x"}]})
        self.assertNotIn("token", cleaned)
        self.assertNotIn("password", cleaned["nested"][0])
        self.assertEqual(cleaned["status"], "ok")


if __name__ == "__main__":
    unittest.main()
