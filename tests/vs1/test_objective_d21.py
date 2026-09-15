"""VS-D21 tests T01-T34: objective gate (HOLD without objective, lawful PASS
only with a valid supplied objective; never invented, never executed).
"""
from __future__ import annotations

import ast
import hashlib
import json
import unittest

from vertical_slice import objective_d21 as D21

D20_PATH = "vertical_slice/post_decision_d20_evidence.json"
D19_PATH = "vertical_slice/evolution_decision_d19_evidence.json"
D12_PATH = "vertical_slice/evolution_decision_v2_evidence.json"
D21_EVIDENCE = "vertical_slice/objective_d21_evidence.json"

# Synthetic fixture exercising the validation machinery ONLY. It is test
# data, not an authorized objective, and no test may treat it as opening a
# real cycle against the committed evidence (see T34).
SYNTHETIC_OBJECTIVE = {
    "objective_id": "vs1-test-objective-synthetic",
    "objective_type": "requirement_delta_test",
    "objective_statement": "Synthetic test statement for validator exercise.",
    "source": "explicit_authorization",
    "source_reference": "test-fixture-only",
    "affected_obligations": ["req-test-only"],
    "scope": {"in_scope": ["test.op-a"], "out_of_scope": ["test.op-b"]},
    "constraints": ["test-only"],
    "success_criteria": [{"criterion": "Synthetic check.",
                          "measurement": "test assertion outcome."}],
    "security_constraints": ["no weakening (test)"],
    "authorization_reference": "test-fixture-only",
}


class Upstream(unittest.TestCase):
    def test_t01_d20_resolves(self):
        record = D21._load_json(D20_PATH)
        self.assertEqual(record.get("contract"), "vs1-post-decision-d20")

    def test_t02_d20_hash_verifies(self):
        record = D21._load_json(D20_PATH)
        check = {k: v for k, v in record.items()
                 if k not in ("provenance", "closure_hash")}
        provenance = dict(record["provenance"])
        provenance.pop("generated_at", None)
        check["provenance"] = provenance
        digest = hashlib.sha256(json.dumps(
            check, sort_keys=True, separators=(",", ":"),
            ensure_ascii=False).encode()).hexdigest()
        self.assertEqual(digest, record["closure_hash"])

    def test_t03_d19_resolves(self):
        self.assertEqual(D21._load_json(D19_PATH).get("decision"), "NO_ACTION")

    def test_t04_d19_no_action(self):
        self.assertEqual(D21.verify_upstream()["d19_decision"], "NO_ACTION")

    def test_t05_d12_no_change(self):
        self.assertEqual(D21._load_json(D12_PATH).get("decision"), "NO_CHANGE")

    def test_t06_real_authorization_zero(self):
        evidence = json.load(open(D21_EVIDENCE, encoding="utf-8"))
        self.assertEqual(evidence["real_authorization"], 0)

    def test_t07_isr_verifies(self):
        self.assertEqual(D21.verify_upstream()["isr_hash"], D21.EXPECTED_ISR)

    def test_t08_integrity(self):
        from vertical_slice import regeneration as REG
        from vertical_slice import deployment_v2 as DEP
        self.assertEqual(REG.build_evidence()["implementation_hash"],
                         "d2090df69127e9922494bb7a4d526de087fd948ee793bdf326d5fe18fac1dd8c")
        self.assertEqual(DEP.contract_hash(),
                         "279fd4da7a47672cac211faf4da934208b9d2f66d8ed5d695fd7f4f7aa8f1dee")


class HoldPath(unittest.TestCase):
    def test_t09_missing_objective_hold(self):
        outcome = D21.define_cycle(None)
        self.assertEqual(outcome["status"], "HOLD")
        self.assertIs(outcome["cycle_opened"], False)

    def test_t10_empty_objective_hold(self):
        outcome = D21.define_cycle({})
        self.assertEqual(outcome["status"], "HOLD")
        self.assertIs(outcome["objective_present"], False)

    def test_t11_malformed_fails_closed(self):
        with self.assertRaises(D21.ObjectiveError):
            D21.validate_objective({"objective_id": "x"})
        with self.assertRaises(D21.ObjectiveError):
            D21.validate_objective("not-a-record")
        with self.assertRaises(D21.ObjectiveError):
            D21.define_cycle({"objective_id": "x"})


class ObjectiveQuality(unittest.TestCase):
    def test_t12_source_traceable(self):
        canonical = D21.validate_objective(dict(SYNTHETIC_OBJECTIVE))
        self.assertEqual(canonical["source"], "explicit_authorization")

    def test_t13_scope_explicit(self):
        canonical = D21.validate_objective(dict(SYNTHETIC_OBJECTIVE))
        self.assertIn("test.op-a", canonical["scope"]["in_scope"])
        self.assertIn("test.op-b", canonical["scope"]["out_of_scope"])

    def test_t14_bounds_explicit(self):
        canonical = D21.validate_objective(dict(SYNTHETIC_OBJECTIVE))
        self.assertTrue(canonical["constraints"])

    def test_t15_success_criteria_explicit(self):
        canonical = D21.validate_objective(dict(SYNTHETIC_OBJECTIVE))
        self.assertTrue(canonical["success_criteria"][0]["measurement"])

    def test_t16_security_preserved(self):
        canonical = D21.validate_objective(dict(SYNTHETIC_OBJECTIVE))
        self.assertTrue(canonical["security_constraints"])

    def test_t30_forbidden_source_fails(self):
        for source in D21.FORBIDDEN_SOURCES:
            bad = dict(SYNTHETIC_OBJECTIVE, source=source)
            with self.assertRaises(D21.ObjectiveError, msg=source):
                D21.validate_objective(bad)

    def test_t31_scope_violation(self):
        canonical = D21.validate_objective(dict(SYNTHETIC_OBJECTIVE))
        self.assertTrue(D21.operation_in_scope(canonical, "test.op-a"))
        self.assertFalse(D21.operation_in_scope(canonical, "test.op-b"))
        self.assertFalse(D21.operation_in_scope(canonical, "test.op-undeclared"))

    def test_t32_no_criteria_fails(self):
        bad = dict(SYNTHETIC_OBJECTIVE, success_criteria=[])
        with self.assertRaises(D21.ObjectiveError):
            D21.validate_objective(bad)
        bad2 = dict(SYNTHETIC_OBJECTIVE,
                    success_criteria=[{"criterion": "Vague."}])
        with self.assertRaises(D21.ObjectiveError):
            D21.validate_objective(bad2)

    def test_t33_no_lineage_fails(self):
        bad = dict(SYNTHETIC_OBJECTIVE, authorization_reference="")
        with self.assertRaises(D21.ObjectiveError):
            D21.validate_objective(bad)
        bad2 = dict(SYNTHETIC_OBJECTIVE)
        del bad2["source_reference"]
        with self.assertRaises(D21.ObjectiveError):
            D21.validate_objective(bad2)


class NonMutationFirewall(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        src = open(D21.__file__, encoding="utf-8").read()
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

    def _sha(self, path: str) -> str:
        with open(path, "rb") as f:
            return hashlib.sha256(f.read()).hexdigest()

    def test_t17_isr_unchanged(self):
        before = D21.verify_upstream()["isr_hash"]
        D21.define_cycle(None)
        D21.assemble_evidence(None, "2026-01-01T00:00:00+00:00")
        self.assertEqual(D21.verify_upstream()["isr_hash"], before)

    def test_t18_d19_unchanged(self):
        before = self._sha(D19_PATH)
        D21.define_cycle(None)
        self.assertEqual(self._sha(D19_PATH), before)

    def test_t19_d20_unchanged(self):
        before = self._sha(D20_PATH)
        D21.define_cycle(None)
        D21.assemble_evidence(None, "2026-01-01T00:00:00+00:00")
        self.assertEqual(self._sha(D20_PATH), before)

    def _assert_no_call(self, names: set[str]):
        for name in names:
            self.assertNotIn(name, self.called, (name, self.called))

    def test_t20_no_candidate_generation(self):
        self.assertLessEqual(self.imports, {"__future__", "hashlib", "json",
                                            "typing", "vertical_slice"},
                             self.imports)
        self._assert_no_call({"generate", "candidates", "propose"})

    def test_t21_no_architecture_selection(self):
        self._assert_no_call({"choose_candidate", "select", "rank"})

    def test_t22_no_implementation(self):
        self._assert_no_call({"compile", "emit", "render"})
        self.assertNotIn("vertical_slice/app_v2/", self.src)

    def test_t23_no_deployment(self):
        self._assert_no_call({"Popen", "deploy", "uvicorn"})

    def test_t24_no_observation(self):
        self._assert_no_call({"observe", "run_online_workload", "launch"})

    def test_t25_no_optimization(self):
        self._assert_no_call({"optimize", "tune"})

    def test_t26_no_production_grant(self):
        evidence = json.load(open(D21_EVIDENCE, encoding="utf-8"))
        self.assertIs(evidence["production_authorization"], False)
        self.assertNotIn("production_authorization = True", self.src)

    def test_t27_no_push(self):
        self.assertNotIn("subprocess", self.imports | self.called)
        for token in ("git push", "git commit"):
            self.assertNotIn(token, self.src, token)


class DeterminismAndHold(unittest.TestCase):
    def test_t28_deterministic(self):
        first = D21.validate_objective(dict(SYNTHETIC_OBJECTIVE))
        second = D21.validate_objective(dict(SYNTHETIC_OBJECTIVE))
        self.assertEqual(first["objective_hash"], second["objective_hash"])

    def test_t29_repeated_identical(self):
        first = D21.assemble_evidence(None, "2026-01-01T00:00:00+00:00")
        second = D21.assemble_evidence(None, "2027-05-05T00:00:00+00:00")
        self.assertEqual(first["objective_evidence_hash"],
                         second["objective_evidence_hash"])
        self.assertEqual(first["status"], "HOLD")

    def test_t34_waiting_state(self):
        evidence = json.load(open(D21_EVIDENCE, encoding="utf-8"))
        self.assertEqual(evidence["status"], "HOLD")
        self.assertIs(evidence["cycle_opened"], False)
        self.assertIs(evidence["objective_present"], False)
        self.assertIsNone(evidence["objective"])
        self.assertEqual(evidence["next"], "WAITING_FOR_EXPLICIT_AUTHORIZATION")
        for key in ("candidate_generation", "architecture_selection",
                    "implementation", "deployment", "observation",
                    "optimization"):
            self.assertEqual(evidence["cycle"][key], "NOT_PERFORMED", key)


if __name__ == "__main__":
    unittest.main()
