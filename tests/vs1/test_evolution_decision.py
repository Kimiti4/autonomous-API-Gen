"""VS-D08 tests T01-T20: deterministic evolution decision (authority only)."""
from __future__ import annotations

import unittest

from vertical_slice import evolution_decision as DEC


class UpstreamIdentities(unittest.TestCase):
    def test_t01_d01(self):
        evidence = DEC.load_interpretation()
        identities = DEC.upstream_identities(evidence)
        self.assertEqual(
            identities["vs-d01-graph-sha256"],
            "28548494e754e9b8214e9f72511a7ba0187fa3378264306a82ff8868bd2e5526")

    def test_t02_d02(self):
        evidence = DEC.load_interpretation()
        identities = DEC.upstream_identities(evidence)
        self.assertEqual(
            identities["vs-d02-isr-content-hash"],
            "48e53dcef47aad84e52e20ec116f5b1f9616a626f42d1c281e3cc26cdf8e9dfb")

    def test_t03_d03(self):
        evidence = DEC.load_interpretation()
        identities = DEC.upstream_identities(evidence)
        self.assertEqual(identities["vs-d03-selected"], "vs1-candidate-a")
        self.assertEqual(identities["vs-d03-policy"], "vs1-selection-v1")

    def test_t04_d04(self):
        from vertical_slice import implementation as IMPL
        self.assertEqual(IMPL.IMPLEMENTATION_VERSION, "vs1-impl-v1")

    def test_t05_d05(self):
        from vertical_slice.deployment import (
            CANDIDATE_ID,
            DEPLOYMENT_CONTRACT_VERSION,
        )
        self.assertEqual(CANDIDATE_ID, "vs1-candidate-a")
        self.assertEqual(DEPLOYMENT_CONTRACT_VERSION, "vs1-deploy-v1")

    def test_t06_d06(self):
        from vertical_slice import observation as OBS
        self.assertEqual(OBS.OBSERVATION_CONTRACT_VERSION, "vs1-observe-v1")


class DecisionBehavior(unittest.TestCase):
    def test_t02_deterministic(self):
        self.assertEqual(DEC.decide(), DEC.decide())

    def test_t03_reordered_inputs(self):
        evidence = DEC.load_interpretation()
        flipped = dict(evidence)
        flipped["hypotheses"] = list(reversed(evidence["hypotheses"]))
        self.assertEqual(DEC.decide(flipped)["decision"],
                         DEC.decide(evidence)["decision"])
        self.assertEqual(DEC.decide(flipped)["content_hash"],
                         DEC.decide(evidence)["content_hash"])

    def test_t04_eligible_reaches_gate(self):
        evidence = DEC.load_interpretation()
        evaluations = [DEC.evaluate_hypothesis(h, evidence)
                       for h in evidence["hypotheses"]]
        by_id = {e["hypothesis_id"]: e["disposition"] for e in evaluations}
        self.assertEqual(by_id["vs1-hypothesis-sufficient-bounded"], "NO_ACTION")

    def test_t05_deferred_cannot_authorize(self):
        evidence = DEC.load_interpretation()
        evaluations = [DEC.evaluate_hypothesis(h, evidence)
                       for h in evidence["hypotheses"]]
        deferred = [e for e in evaluations if e["disposition"] == "DEFER"]
        self.assertEqual(len(deferred), 2)
        decision = DEC.decide(evidence)
        self.assertNotEqual(decision["decision"], "AUTHORIZE_EVOLUTION")

    def test_t19_unique_decision(self):
        decision = DEC.decide()
        self.assertIn(decision["decision"],
                      ("NO_CHANGE", "REQUEST_MORE_EVIDENCE",
                       "AUTHORIZE_EVOLUTION", "REJECT_EVOLUTION"))
        self.assertEqual(decision["decision"], "NO_CHANGE")

    def test_t20_provenance_complete(self):
        decision = DEC.decide()
        self.assertTrue(decision["provenance"])
        for key in ("vs-d01-graph-sha256", "vs-d02-isr-content-hash",
                    "vs-d03-selected"):
            self.assertIn(key, decision["provenance"])
        self.assertEqual(
            sorted(decision["reviewed_hypotheses"]),
            ["vs1-hypothesis-auth-model-adequate",
             "vs1-hypothesis-deploy-repeatable",
             "vs1-hypothesis-sufficient-bounded"])


class FailClosed(unittest.TestCase):
    def test_t06_missing_evidence(self):
        with self.assertRaises(Exception):
            DEC.load_interpretation("vertical_slice/does-not-exist.json")

    def test_t07_missing_falsifier(self):
        import copy
        evidence = DEC.load_interpretation()
        broken = copy.deepcopy(evidence)
        broken["hypotheses"][0] = dict(broken["hypotheses"][0], falsifiers=[])
        with self.assertRaises(DEC.DecisionError):
            DEC.decide(broken)

    def test_t08_contradiction(self):
        import copy
        evidence = DEC.load_interpretation()
        broken = copy.deepcopy(evidence)
        broken["contradictions"] = [{"contradiction_id": "x", "status": "contradicted"}]
        decision = DEC.decide(broken)
        self.assertEqual(decision["decision"], "REJECT_EVOLUTION")

    def test_t09_scope_violation(self):
        import copy
        evidence = DEC.load_interpretation()
        broken = copy.deepcopy(evidence)
        bad = dict(broken["hypotheses"][0])
        bad["hypothesis_id"] = "vs1-hypothesis-scope-test"
        bad["statement"] = ("The system requires a requirement change to add "
                            "unmanaged tenants.")
        bad["evolution_eligibility"] = "eligible_for_evolution_review"
        broken["hypotheses"] = [bad]
        with self.assertRaises(DEC.DecisionError):
            DEC.decide(broken)


class Protection(unittest.TestCase):
    def test_t10_isr_protection(self):
        import ast
        import os
        src = open(os.path.join("vertical_slice", "evolution_decision.py"),
                   encoding="utf-8").read()
        tree = ast.parse(src)
        identifiers: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Name):
                identifiers.add(node.id.lower())
            elif isinstance(node, ast.Attribute):
                identifiers.add(node.attr.lower())
        for token in ("mutate", "crossover", "compile", "deploy", "uvicorn",
                      "docker", "retire", "migrate", "patch", "rewrite"):
            self.assertNotIn(token, identifiers, token)

    def test_t11_requirement_protection(self):
        decision = DEC.decide()
        blob = str(decision).lower()
        for marker in ("rewrite requirement", "new requirement",
                       "mutate requirement", "change the isr"):
            self.assertNotIn(marker, blob, marker)


class Requirements(unittest.TestCase):
    def test_t12_no_source_patches(self):
        decision = DEC.decide()
        self.assertIsNone(decision["authorized_objective"])
        self.assertNotIn("files to patch", str(decision))

    def test_t13_rollback_required(self):
        self.assertIn("rollback capability required", " ".join(
            DEC.decide()["constraints"]).lower())

    def test_t14_verification_required(self):
        self.assertIn("verification gates preserved", " ".join(
            DEC.decide()["constraints"]).lower())

    def test_t15_deployment_required(self):
        self.assertIn("deployment provenance preserved", " ".join(
            DEC.decide()["constraints"]).lower())

    def test_t16_observation_required(self):
        self.assertIn("observation provenance preserved", " ".join(
            DEC.decide()["constraints"]).lower())

    def test_t17_no_change_valid(self):
        decision = DEC.decide()
        self.assertEqual(decision["decision"], "NO_CHANGE")
        self.assertIn("acceptable", decision["decision_rationale"])

    def test_t18_more_evidence_valid(self):
        import copy
        evidence = DEC.load_interpretation()
        stripped = copy.deepcopy(evidence)
        stripped["hypotheses"] = [
            h for h in stripped["hypotheses"]
            if h["evolution_eligibility"] != "eligible_for_evolution_review"]
        decision = DEC.decide(stripped)
        self.assertEqual(decision["decision"], "REQUEST_MORE_EVIDENCE")


if __name__ == "__main__":
    unittest.main()
