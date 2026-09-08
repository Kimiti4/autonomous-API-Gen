"""VS-D12 tests T01-T40: evolution decision gate (authority only)."""
from __future__ import annotations

import unittest

from vertical_slice import evolution_decision_v2 as DEC


class UpstreamIdentities(unittest.TestCase):
    def test_t01_d01(self):
        self.assertEqual(
            DEC.upstream_identities(DEC.load_d11())["vs-d01-graph-sha256"],
            "28548494e754e9b8214e9f72511a7ba0187fa3378264306a82ff8868bd2e5526")

    def test_t02_d02(self):
        self.assertEqual(
            DEC.upstream_identities(DEC.load_d11())["vs-d02-isr-content-hash"],
            "48e53dcef47aad84e52e20ec116f5b1f9616a626f42d1c281e3cc26cdf8e9dfb")

    def test_t03_d03(self):
        self.assertEqual(DEC.upstream_identities(DEC.load_d11())["vs-d03-selected"],
                         "vs1-candidate-a")

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

    def test_t07_d07(self):
        import json
        evidence = json.load(open("vertical_slice/interpretation_evidence.json"))
        self.assertEqual(len(evidence["hypotheses"]), 3)

    def test_t08_d08(self):
        self.assertEqual(DEC.upstream_identities(DEC.load_d11())["vs-d08-decision"],
                         "NO_CHANGE")

    def test_t09_d09(self):
        from vertical_slice import evidence_acquisition as ACQ
        gate = ACQ.run_gate()
        self.assertEqual(gate["outcome"], "EVIDENCE_PLAN_REQUIRED")

    def test_t10_plan_integrity(self):
        from vertical_slice import evidence_acquisition as ACQ
        for plan in ACQ.run_gate()["plans"]:
            ACQ.check_plan_integrity(plan)

    def test_t11_d11_identity(self):
        evidence = DEC.load_d11()
        self.assertEqual(len(evidence["hypotheses"]), 2)
        self.assertEqual(evidence["contract"], "vs1-interpretation-v2")


class Eligibility(unittest.TestCase):
    def test_t12_d08_immutable(self):
        from vertical_slice import evolution_decision as DEC1
        self.assertEqual(DEC1.decide()["decision"], "NO_CHANGE")
        self.assertEqual(DEC.upstream_identities(DEC.load_d11())["vs-d08-decision"],
                         "NO_CHANGE")

    def test_t13_valid_provenance(self):
        decision = DEC.decide()
        for key in ("vs-d01-graph-sha256", "vs-d02-isr-content-hash",
                    "vs-d03-selected"):
            self.assertIn(key, decision["provenance"])

    def test_t14_hypothesis_states(self):
        for hypothesis in DEC.load_d11()["hypotheses"]:
            self.assertIn(hypothesis["updated_status"],
                          ("SUFFICIENTLY_SUPPORTED", "REMAINS_WEAKLY_SUPPORTED",
                           "REQUIRES_MORE_EVIDENCE", "CONTRADICTED"))

    def test_t15_falsifiers(self):
        for hypothesis in DEC.load_d11()["hypotheses"]:
            self.assertTrue(hypothesis["falsifier"])
            self.assertIn(hypothesis["falsifier_status"],
                          ("NOT_TRIGGERED", "TRIGGERED", "UNDETERMINED"))

    def test_t16_contradictions(self):
        self.assertEqual(DEC.load_d11()["contradictions"], [])


class NoChangePath(unittest.TestCase):
    def test_t17_supported_not_authorization(self):
        decision = DEC.decide()
        self.assertEqual(decision["decision"], "NO_CHANGE")
        self.assertIsNone(decision["authorized_objective"])

    def test_t18_current_state_no_change(self):
        decision = DEC.decide()
        self.assertIn("acceptable", decision["decision_rationale"])
        self.assertEqual(
            [e["disposition"] for e in decision["evaluations"]],
            ["NO_ACTION", "NO_ACTION"])

    def test_t19_unsupported_objective_blocked(self):
        import copy
        evidence = copy.deepcopy(DEC.load_d11())
        del evidence["hypotheses"][0]["falsifier"]
        decision = DEC.decide(evidence)
        self.assertEqual(decision["decision"], "BLOCKED")


class AuthorizePath(unittest.TestCase):
    def _problem_evidence(self):
        import copy
        evidence = copy.deepcopy(DEC.load_d11())
        target = dict(evidence["hypotheses"][0])
        target["hypothesis_id"] = "vs1-hypothesis-synthetic-problem"
        target["problem"] = {
            "statement": ("Repeated bounded authorization probes show "
                          "stale sessions remain valid after logout."),
            "evidence_basis": [target["supporting_observations"][0]],
            "scope": "session lifecycle behavior",
            "desired_outcome": "sessions invalidate on logout",
            "success_measure": "post-logout token rejected in bounded probes",
        }
        evidence["hypotheses"] = [target]
        return evidence

    def test_t20_authorize_path(self):
        decision = DEC.decide(self._problem_evidence())
        self.assertEqual(decision["decision"], "AUTHORIZE_EVOLUTION")
        objective = decision["authorized_objective"]
        self.assertIsNotNone(objective)
        for field in ("objective_id", "problem_statement", "evidence_basis",
                      "affected_scope", "desired_outcome", "success_measure",
                      "constraints", "rollback_requirement",
                      "verification_requirement", "deployment_requirement",
                      "observation_requirement", "magnitude"):
            self.assertIn(field, objective, field)

    def test_t21_objective_bounded(self):
        decision = DEC.decide(self._problem_evidence())
        objective = decision["authorized_objective"]
        self.assertIn(objective["magnitude"],
                      ("LOCAL_OPTIMIZATION", "BEHAVIORAL_CHANGE",
                       "ARCHITECTURAL_CHANGE"))

    def test_t22_rollback(self):
        decision = DEC.decide(self._problem_evidence())
        self.assertIn("restorable",
                      decision["authorized_objective"]["rollback_requirement"])

    def test_t23_verification(self):
        decision = DEC.decide(self._problem_evidence())
        self.assertIn("reverification",
                      decision["authorized_objective"]["verification_requirement"])

    def test_t24_deployment(self):
        decision = DEC.decide(self._problem_evidence())
        self.assertIn("controlled deployment",
                      decision["authorized_objective"]["deployment_requirement"])

    def test_t25_observation(self):
        decision = DEC.decide(self._problem_evidence())
        self.assertIn("post-deployment observation",
                      decision["authorized_objective"]["observation_requirement"])


class RejectBlockedPaths(unittest.TestCase):
    def test_t26_contradicted(self):
        import copy
        evidence = copy.deepcopy(DEC.load_d11())
        bad = dict(evidence["hypotheses"][0])
        bad["updated_status"] = "CONTRADICTED"
        evidence["hypotheses"] = [bad]
        evidence["contradictions"] = [{"contradiction_id": "x",
                                       "status": "contradicted"}]
        decision = DEC.decide(evidence)
        self.assertEqual(decision["decision"], "REJECT_EVOLUTION")

    def test_t27_malformed(self):
        import copy
        evidence = copy.deepcopy(DEC.load_d11())
        del evidence["hypotheses"]
        decision = DEC.decide(evidence)
        self.assertEqual(decision["decision"], "BLOCKED")

    def test_t28_missing_provenance(self):
        import copy
        evidence = copy.deepcopy(DEC.load_d11())
        evidence["hypotheses"][0] = dict(evidence["hypotheses"][0])
        del evidence["hypotheses"][0]["supporting_findings"]
        decision = DEC.decide(evidence)
        self.assertEqual(decision["decision"], "BLOCKED")

    def test_t29_deterministic(self):
        import json
        first = json.dumps(DEC.decide(), sort_keys=True)
        second = json.dumps(DEC.decide(), sort_keys=True)
        self.assertEqual(first, second)

    def test_t30_hash(self):
        import hashlib
        import json
        decision = DEC.decide()
        recomputed = hashlib.sha256(json.dumps(
            {k: v for k, v in decision.items() if k != "content_hash"},
            sort_keys=True, separators=(",", ":")).encode()).hexdigest()
        self.assertEqual(decision["content_hash"], recomputed)


class Firewalls(unittest.TestCase):
    def test_t31_isr(self):
        import ast
        import os
        src = open(os.path.join("vertical_slice", "evolution_decision_v2.py"),
                   encoding="utf-8").read()
        tree = ast.parse(src)
        identifiers: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Name):
                identifiers.add(node.id.lower())
            elif isinstance(node, ast.Attribute):
                identifiers.add(node.attr.lower())
        for token in ("mutate", "crossover", "compile", "deploy", "uvicorn",
                      "docker", "retire", "migrate", "patch", "rewrite",
                      "generate_candidate", "select_candidate"):
            self.assertNotIn(token, identifiers, token)

    def test_t32_requirements(self):
        decision = DEC.decide()
        blob = str(decision).lower()
        for marker in ("new requirement", "rewrite requirement", "change the isr"):
            self.assertNotIn(marker, blob, marker)

    def test_t33_d08_mutation(self):
        from vertical_slice import evolution_decision as DEC1
        before = DEC1.decide()
        DEC.decide()
        self.assertEqual(DEC1.decide(), before)

    def test_t34_d10_mutation(self):
        import json
        before = open("vertical_slice/evidence_acquisition_results.json",
                      encoding="utf-8").read()
        DEC.decide()
        after = open("vertical_slice/evidence_acquisition_results.json",
                     encoding="utf-8").read()
        self.assertEqual(before, after)
        json.loads(after)

    def test_t35_d11_mutation(self):
        import json
        before = open("vertical_slice/interpretation_v2_evidence.json",
                      encoding="utf-8").read()
        DEC.decide()
        after = open("vertical_slice/interpretation_v2_evidence.json",
                     encoding="utf-8").read()
        self.assertEqual(before, after)

    def test_t36_candidate_generation(self):
        decision = DEC.decide()
        self.assertNotIn("candidates", decision)
        self.assertNotIn("selected_candidate", str(decision))

    def test_t37_implementation(self):
        import ast
        import os
        src = open(os.path.join("vertical_slice", "evolution_decision_v2.py"),
                   encoding="utf-8").read()
        self.assertNotIn("vertical_slice.app", src)
        self.assertNotIn("implementation.py", src)

    def test_t38_deployment(self):
        decision = DEC.decide()
        blob = str(decision).lower()
        self.assertNotIn("uvicorn", blob)
        self.assertNotIn("docker", blob)

    def test_t39_redeployment(self):
        decision = DEC.decide()
        self.assertNotIn("authorization", decision)
        self.assertIsNone(decision["authorized_objective"])

    def test_t40_secrets(self):
        import json
        blob = json.dumps(DEC.decide()).lower()
        for marker in ("alice-secret", "bob-secret", "cara-secret", "eve-secret",
                       "vs1-test-token", "vs1-deploy-token", "vs1-obs-token",
                       "vs1-d10-token", "password"):
            self.assertNotIn(marker, blob, marker)


if __name__ == "__main__":
    unittest.main()
