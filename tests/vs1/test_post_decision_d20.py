"""VS-D20 tests T01-T24: post-decision closure (holds NO_ACTION, grants nothing).

Static suite. Tamper tests use temp copies only; no upstream artifact is
written by any test.
"""
from __future__ import annotations

import ast
import hashlib
import json
import os
import tempfile
import unittest

from vertical_slice import post_decision_d20 as D20

D19_PATH = "vertical_slice/evolution_decision_d19_evidence.json"
D18_PATH = "vertical_slice/runtime_interpretation_evidence.json"
D17_PATH = "vertical_slice/runtime_observation_evidence.json"
D12_PATH = "vertical_slice/evolution_decision_v2_evidence.json"
D20_EVIDENCE = "vertical_slice/post_decision_d20_evidence.json"


def _sha_file(path: str) -> str:
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def _tampered_copy(path: str, mutate) -> str:
    tmp = tempfile.NamedTemporaryFile(
        mode="w", suffix=".json", delete=False, encoding="utf-8")
    record = json.load(open(path, encoding="utf-8"))
    mutate(record)
    tmp.write(json.dumps(record))
    tmp.close()
    return tmp.name


class Resolution(unittest.TestCase):
    def test_t01_d19_resolves(self):
        record = D20._load_json(D19_PATH)
        self.assertEqual(record.get("decision"), "NO_ACTION")

    def test_t02_d19_hash_verifies(self):
        lineage = D20.verify_lineage()
        self.assertEqual(lineage["D20→D19"], "VERIFIED")

    def test_t03_d18_lineage_verifies(self):
        lineage = D20.verify_lineage()
        self.assertEqual(lineage["D19→D18"], "VERIFIED")

    def test_t04_d17_lineage_verifies(self):
        d18 = json.load(open(D18_PATH, encoding="utf-8"))
        d17 = json.load(open(D17_PATH, encoding="utf-8"))
        self.assertEqual(d18["evidence_hash"], d17["normalized_hash"])
        self.assertEqual(D20.verify_lineage()["D18→D17"], "VERIFIED")

    def test_t05_d12_no_change(self):
        self.assertEqual(json.load(open(D12_PATH, encoding="utf-8")
                                   ).get("decision"), "NO_CHANGE")

    def test_t06_real_authorization_zero(self):
        authority = D20.verify_authority()
        evidence = json.load(open(D19_PATH, encoding="utf-8"))
        self.assertEqual(evidence["d12_authorization"], 0)
        self.assertIn("NO EVOLUTION AUTHORIZED", authority["conclusion"])

    def test_t07_evolution_none(self):
        authority = D20.verify_authority()
        self.assertEqual(authority["evolution_authorization"], "NONE")
        self.assertEqual(authority["change_authorization"], "NONE")
        self.assertEqual(authority["deployment_authorization"], "NONE")
        self.assertEqual(authority["push_authorization"], "NONE")

    def test_t08_production_false(self):
        authority = D20.verify_authority()
        self.assertIs(authority["production_authorization"], False)


class ClosurePreservation(unittest.TestCase):
    def test_t09_findings_no_action(self):
        closure = D20.verify_closure()
        self.assertEqual(closure["findings_preserved"], "10/10")

    def test_t10_unknowns_preserved(self):
        self.assertEqual(D20.verify_closure()["unknowns_preserved"], "7/7")
        d18 = json.load(open(D18_PATH, encoding="utf-8"))
        self.assertEqual(len(d18["unknowns"]), 7)

    def test_t11_scope_preserved(self):
        self.assertEqual(
            D20.verify_closure()["scope_constraints_preserved"], "PASS")

    def test_t12_isr_unchanged(self):
        from vertical_slice import implementation as IMPL
        self.assertEqual(
            IMPL.frozen_input_identity()["vs-d02-isr-content-hash"],
            D20.EXPECTED_ISR)

    def test_t13_d01_d19_unchanged(self):
        from vertical_slice import regeneration as REG
        from vertical_slice import deployment_v2 as DEP
        self.assertEqual(REG.build_evidence()["implementation_hash"],
                         "d2090df69127e9922494bb7a4d526de087fd948ee793bdf326d5fe18fac1dd8c")
        self.assertEqual(DEP.contract_hash(),
                         "279fd4da7a47672cac211faf4da934208b9d2f66d8ed5d695fd7f4f7aa8f1dee")


class Firewall(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        src = open(D20.__file__, encoding="utf-8").read()
        tree = ast.parse(src)
        cls.imports: set[str] = set()
        cls.called: set[str] = set()
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
        cls.src = src

    def test_t14_no_evolution(self):
        self.assertLessEqual(self.imports, {"__future__", "hashlib", "json",
                                            "typing", "vertical_slice"},
                             self.imports)
        for name in ("generate", "candidates", "mutate", "retire",
                     "crossover", "choose_candidate", "select", "evolve"):
            self.assertNotIn(name, self.called, (name, self.called))

    def test_t15_no_implementation(self):
        for name in ("compile", "emit", "render"):
            self.assertNotIn(name, self.called, (name, self.called))
        self.assertNotIn("vertical_slice/app_v2/", self.src)

    def test_t16_no_deployment(self):
        for name in ("Popen", "deploy", "uvicorn"):
            self.assertNotIn(name, self.called, (name, self.called))

    def test_t17_no_observation(self):
        for name in ("observe", "run_online_workload", "launch"):
            self.assertNotIn(name, self.called, (name, self.called))

    def test_t18_no_optimization(self):
        for name in ("optimize", "tune", "improve"):
            self.assertNotIn(name, self.called, (name, self.called))

    def test_t19_no_production_grant(self):
        evidence = json.load(open(D20_EVIDENCE, encoding="utf-8"))
        self.assertIs(evidence["authority"]["production_authorization"], False)
        self.assertNotIn("production_authorization = True", self.src)

    def test_t20_no_push(self):
        self.assertNotIn("subprocess", self.imports | self.called)
        for token in ("git push", "git commit"):
            self.assertNotIn(token, self.src, token)


class CanonicalClosure(unittest.TestCase):
    def test_t21_canonical(self):
        raw = open(D20_EVIDENCE, encoding="utf-8").read()
        self.assertEqual(raw, json.dumps(json.loads(raw), sort_keys=True,
                                         separators=(",", ":"),
                                         ensure_ascii=False) + "\n")

    def test_t22_authority_deterministic(self):
        self.assertEqual(D20.verify_authority(), D20.verify_authority())
        self.assertEqual(D20.determine_next_state(),
                         {"next_gate": "NONE",
                          "pipeline_state": "WAITING_FOR_EXPLICIT_AUTHORIZATION",
                          "evolution_action": "NO_EVOLUTION_ACTION"})

    def test_t23_repeated_identical(self):
        first = D20.assemble_closure("2026-01-01T00:00:00+00:00")
        second = D20.assemble_closure("2027-05-05T00:00:00+00:00")
        self.assertEqual(first["closure_hash"], second["closure_hash"])

    def test_t24_forged_continuation_fails_closed(self):
        forged = _tampered_copy(
            D19_PATH, lambda r: r.__setitem__("decision", "EVOLUTION_PROPOSED"))
        self.addCleanup(lambda: os.unlink(forged))
        with self.assertRaises(D20.ClosureError):
            D20.verify_authority(d19_path=forged)
        with self.assertRaises(D20.ClosureError):
            D20.verify_closure(d19_path=forged)
        granted = _tampered_copy(
            D19_PATH, lambda r: r.__setitem__("evolution_authorization", "GRANTED"))
        self.addCleanup(lambda: os.unlink(granted))
        with self.assertRaises(D20.ClosureError):
            D20.verify_authority(d19_path=granted)


if __name__ == "__main__":
    unittest.main()
