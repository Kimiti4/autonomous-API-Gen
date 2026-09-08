"""VS-D09 tests T01-T20: evidence acquisition gate (planning only)."""
from __future__ import annotations

import unittest

from vertical_slice import evidence_acquisition as ACQ


class UpstreamIdentities(unittest.TestCase):
    def test_t01_d01_d08_identities(self):
        decision = ACQ.load_decision()
        identities = ACQ.upstream_identities(decision)
        self.assertEqual(
            identities["vs-d01-graph-sha256"],
            "28548494e754e9b8214e9f72511a7ba0187fa3378264306a82ff8868bd2e5526")
        self.assertEqual(
            identities["vs-d02-isr-content-hash"],
            "48e53dcef47aad84e52e20ec116f5b1f9616a626f42d1c281e3cc26cdf8e9dfb")
        self.assertEqual(identities["vs-d03-selected"], "vs1-candidate-a")
        self.assertEqual(identities["vs-d08-decision"], "vs1-decision-v1")

    def test_t02_consumes_actual_no_change(self):
        decision = ACQ.load_decision()
        self.assertEqual(decision["decision"], "NO_CHANGE")

    def test_t03_deferred_discovery(self):
        hypotheses = ACQ.load_hypotheses()
        deferred = sorted(h["hypothesis_id"] for h in hypotheses
                          if h["evolution_eligibility"] == "requires_more_evidence")
        self.assertEqual(deferred, ["vs1-hypothesis-auth-model-adequate",
                                    "vs1-hypothesis-deploy-repeatable"])

    def test_t04_eligible_protected(self):
        record = ACQ.run_gate()
        planned = {p["hypothesis_id"] for p in record["plans"]}
        self.assertNotIn("vs1-hypothesis-sufficient-bounded", planned)
        self.assertEqual(record["outcome"], "EVIDENCE_PLAN_REQUIRED")


class Gaps(unittest.TestCase):
    def test_t05_auth_gap(self):
        hypotheses = {h["hypothesis_id"]: h for h in ACQ.load_hypotheses()}
        analysis = ACQ.analyze_hypothesis(
            hypotheses["vs1-hypothesis-auth-model-adequate"])
        self.assertIn("role", analysis["unknown_to_resolve"].lower())
        self.assertGreaterEqual(analysis["observation_count"], 1)
        self.assertEqual(analysis["decision_after_evidence"], "REVIEW_AGAIN")

    def test_t06_deploy_gap(self):
        hypotheses = {h["hypothesis_id"]: h for h in ACQ.load_hypotheses()}
        analysis = ACQ.analyze_hypothesis(
            hypotheses["vs1-hypothesis-deploy-repeatable"])
        self.assertIn("independent", (analysis["unknown_to_resolve"]
                                       + analysis["required_observation"]).lower())
        self.assertGreaterEqual(analysis["observation_count"], 2)


class FailClosed(unittest.TestCase):
    def test_t07_missing_falsifier(self):
        import copy
        hypotheses = ACQ.load_hypotheses()
        broken = copy.deepcopy(hypotheses[0])
        broken["falsifiers"] = []
        with self.assertRaises(ACQ.AcquisitionError):
            ACQ.validate_hypothesis(broken)

    def test_t08_missing_objective(self):
        with self.assertRaises(ACQ.AcquisitionError):
            ACQ.load_decision("vertical_slice/does-not-exist.json")

    def test_t09_unbounded(self):
        analysis = {
            "hypothesis_id": "vs1-hypothesis-auth-model-adequate",
            "unknown_to_resolve": "x",
            "required_observation": "y",
            "observation_count": 0,
            "success_criteria": ["s"],
            "falsification_criteria": ["f"],
            "scope": "s",
            "out_of_scope": [],
        }
        with self.assertRaises(ACQ.AcquisitionError):
            ACQ.build_plan(analysis, {})

    def test_t10_mutation_request(self):
        analysis = {
            "hypothesis_id": "vs1-hypothesis-auth-model-adequate",
            "unknown_to_resolve": "requires source-code modification of login",
            "required_observation": "observe",
            "observation_count": 1,
            "success_criteria": ["s"],
            "falsification_criteria": ["f"],
            "scope": "s",
            "out_of_scope": [],
        }
        with self.assertRaises(ACQ.AcquisitionError):
            ACQ.build_plan(analysis, {})

    def test_t11_isr_mutation(self):
        analysis = {
            "hypothesis_id": "vs1-hypothesis-auth-model-adequate",
            "unknown_to_resolve": "requires mutate isr semantics for auth",
            "required_observation": "observe",
            "observation_count": 1,
            "success_criteria": ["s"],
            "falsification_criteria": ["f"],
            "scope": "s",
            "out_of_scope": [],
        }
        with self.assertRaises(ACQ.AcquisitionError):
            ACQ.build_plan(analysis, {})

    def test_t12_requirement_mutation(self):
        analysis = {
            "hypothesis_id": "vs1-hypothesis-auth-model-adequate",
            "unknown_to_resolve": "x",
            "required_observation": "rewrite requirement req-auth-login first",
            "observation_count": 1,
            "success_criteria": ["s"],
            "falsification_criteria": ["f"],
            "scope": "s",
            "out_of_scope": [],
        }
        with self.assertRaises(ACQ.AcquisitionError):
            ACQ.build_plan(analysis, {})

    def test_t13_secret_retention(self):
        analysis = {
            "hypothesis_id": "vs1-hypothesis-auth-model-adequate",
            "unknown_to_resolve": "x",
            "required_observation": "observe",
            "observation_count": 1,
            "success_criteria": ["s"],
            "falsification_criteria": ["f"],
            "scope": "s",
            "out_of_scope": [],
        }
        import copy
        hacked = copy.deepcopy(analysis)
        hacked["required_observation"] = "record password: hunter2 for replay"
        with self.assertRaises(ACQ.AcquisitionError):
            ACQ.build_plan(hacked, {})


class Determinism(unittest.TestCase):
    def test_t14_deterministic(self):
        import json
        first = json.dumps(ACQ.run_gate(), sort_keys=True)
        second = json.dumps(ACQ.run_gate(), sort_keys=True)
        self.assertEqual(first, second)

    def test_t15_reordered(self):
        import json
        hypotheses = ACQ.load_hypotheses()
        forward = [ACQ.build_plan(ACQ.analyze_hypothesis(h), {})
                   for h in hypotheses
                   if h["evolution_eligibility"] == "requires_more_evidence"]
        backward = [ACQ.build_plan(ACQ.analyze_hypothesis(h), {})
                    for h in reversed(hypotheses)
                    if h["evolution_eligibility"] == "requires_more_evidence"]
        self.assertEqual(
            sorted(json.dumps(p, sort_keys=True) for p in forward),
            sorted(json.dumps(p, sort_keys=True) for p in backward))

    def test_t16_provenance(self):
        record = ACQ.run_gate()
        for plan in record["plans"]:
            for field in ("vs-d01-graph-sha256", "vs-d02-isr-content-hash",
                          "vs-d03-selected"):
                self.assertIn(field, plan["provenance"], (plan["plan_id"], field))
        self.assertIn("vs-d08-decision", record["plans"][0]["provenance"])


class Paths(unittest.TestCase):
    def test_t17_no_evidence_path(self):
        self.assertEqual(
            ACQ.determine_outcome([], []), "NO_ADDITIONAL_EVIDENCE_REQUIRED")

    def test_t18_blocked_path(self):
        self.assertEqual(
            ACQ.determine_outcome([], ["h: unsafe"]), "EVIDENCE_PLAN_BLOCKED")

    def test_t19_firewall(self):
        import ast
        import os
        src = open(os.path.join("vertical_slice", "evidence_acquisition.py"),
                   encoding="utf-8").read()
        tree = ast.parse(src)
        identifiers: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Name):
                identifiers.add(node.id.lower())
            elif isinstance(node, ast.Attribute):
                identifiers.add(node.attr.lower())
        for token in ("authorize_evolution", "mutate", "crossover", "compile",
                      "deploy", "uvicorn", "docker", "retire", "migrate",
                      "patch", "rewrite"):
            self.assertNotIn(token, identifiers, token)
        record = ACQ.run_gate()
        self.assertFalse(record["evolution_authorized"])

    def test_t20_artifacts_unchanged(self):
        from vertical_slice import implementation as IMPL
        from vertical_slice import candidates as C
        self.assertEqual(IMPL.IMPLEMENTATION_VERSION, "vs1-impl-v1")
        self.assertEqual(C.select_candidate()["selected"], "vs1-candidate-a")
        self.assertEqual(IMPL.build_evidence()["candidate_id"], "vs1-candidate-a")


if __name__ == "__main__":
    unittest.main()
