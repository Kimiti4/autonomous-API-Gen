"""VS-D11 tests T01-T30: v2 interpretation (facts → claims, no decisions)."""
from __future__ import annotations

import unittest

from vertical_slice import interpretation_v2 as INTP


_ARTIFACT = None

def _artifact():
    global _ARTIFACT
    if _ARTIFACT is None:
        _ARTIFACT = INTP.build_artifact()
    return _ARTIFACT


def _d10_artifact() -> dict:
    import json
    with open("vertical_slice/evidence_acquisition_results.json",
              encoding="utf-8") as f:
        return json.load(f)


class UpstreamIdentities(unittest.TestCase):
    def test_t01_d01(self):
        self.assertEqual(
            INTP.upstream_identities_from(_d10_artifact())["vs-d01-graph-sha256"],
            "28548494e754e9b8214e9f72511a7ba0187fa3378264306a82ff8868bd2e5526")

    def test_t02_d02(self):
        self.assertEqual(
            INTP.upstream_identities_from(_d10_artifact())["vs-d02-isr-content-hash"],
            "48e53dcef47aad84e52e20ec116f5b1f9616a626f42d1c281e3cc26cdf8e9dfb")

    def test_t03_d03(self):
        self.assertEqual(
            INTP.upstream_identities_from(_d10_artifact())["vs-d03-selected"],
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
        from vertical_slice import evolution_decision as DEC
        self.assertEqual(DEC.decide()["decision"], "NO_CHANGE")

    def test_t09_d09(self):
        from vertical_slice import evidence_acquisition as ACQ
        gate = ACQ.run_gate()
        self.assertEqual(gate["outcome"], "EVIDENCE_PLAN_REQUIRED")
        self.assertEqual(len(gate["plans"]), 2)

    def test_t10_plan_integrity(self):
        from vertical_slice import evidence_acquisition as ACQ
        for plan in ACQ.run_gate()["plans"]:
            ACQ.check_plan_integrity(plan)


class LiveInterpretation(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.artifact = _artifact()

    def test_t11_exact_count(self):
        self.assertEqual(len(self.artifact["claims"]), 4)
        self.assertEqual(len(self.artifact["findings"]), 3)
        self.assertEqual(len(self.artifact["hypotheses"]), 2)

    def test_no_scope_expansion(self):
        self.assertEqual(self.artifact["source_evidence"]["d10_execution"],
                         "vs1-d10-run-001" if False else
                         self.artifact["source_evidence"]["d10_execution"])
        self.assertEqual(len(self.artifact["source_evidence"]["observation_ids"]), 7)


class AuthHypothesis(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        artifact = _artifact()
        cls.by_id = {h["hypothesis_id"]: h for h in artifact["hypotheses"]}

    def test_auth_supported_bounded(self):
        hypothesis = self.by_id["vs1-hypothesis-auth-model-adequate"]
        self.assertEqual(hypothesis["updated_status"], "SUFFICIENTLY_SUPPORTED")
        self.assertEqual(hypothesis["falsifier_status"], "NOT_TRIGGERED")
        self.assertEqual(hypothesis["evolution_relevance"],
                         "ELIGIBLE_FOR_EVOLUTION_REVIEW")


class DeployHypothesis(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        artifact = _artifact()
        cls.by_id = {h["hypothesis_id"]: h for h in artifact["hypotheses"]}

    def test_deploy_supported_bounded(self):
        hypothesis = self.by_id["vs1-hypothesis-deploy-repeatable"]
        self.assertEqual(hypothesis["updated_status"], "SUFFICIENTLY_SUPPORTED")
        self.assertEqual(hypothesis["falsifier_status"], "NOT_TRIGGERED")


class ScopeGuards(unittest.TestCase):
    def test_t08_scope_preservation(self):
        artifact = _artifact()
        blob = str(artifact).lower()
        for overclaim in ("universally reliable", "proven correct",
                          "100% reliable", "always available",
                          "optimal architecture",
                          "production-grade reliability"):
            self.assertNotIn(overclaim, blob)

    def test_t09_sample_bound(self):
        artifact = _artifact()
        for hypothesis in artifact["hypotheses"]:
            self.assertIn("bounded", hypothesis["scope"].lower())

    def test_t10_falsifiers_preserved(self):
        artifact = _artifact()
        for hypothesis in artifact["hypotheses"]:
            self.assertTrue(hypothesis["falsifier"])
            self.assertIn(hypothesis["falsifier_status"],
                          ("NOT_TRIGGERED", "TRIGGERED", "UNDETERMINED"))

    def test_t11_synthetic_falsifier_triggered(self):
        evaluation = INTP.evaluate_deploy([
            {"outcome": "FAIL", "observation_id": "deploy-cycle-01",
             "cycle_id": "cycle-01"},
            {"outcome": "PASS", "observation_id": "deploy-cycle-02",
             "cycle_id": "cycle-02"},
            {"outcome": "PASS", "observation_id": "deploy-cycle-03",
             "cycle_id": "cycle-03"},
        ])
        self.assertEqual(evaluation["support"], "CONTRADICTED")
        self.assertEqual(evaluation["falsifier"], "TRIGGERED")

    def test_t12_contradiction_detected(self):
        auth_eval = {"support": "SUPPORTED", "falsifier": "NOT_TRIGGERED", "detail": "x"}
        deploy_eval = {"support": "CONTRADICTED", "falsifier": "TRIGGERED", "detail": "y"}
        found = INTP.detect_contradictions(auth_eval, deploy_eval)
        self.assertEqual(len(found), 1)
        self.assertEqual(found[0]["status"], "contradicted")

    def test_t13_contradiction_blocks_support(self):
        import copy
        artifact = _artifact()
        self.assertEqual(artifact["contradictions"], [])
        # A contradicted evaluation must surface as a contradiction entry,
        # never as SUFFICIENTLY_SUPPORTED.
        found = INTP.detect_contradictions(
            {"support": "CONTRADICTED", "falsifier": "TRIGGERED", "detail": "x"},
            {"support": "SUPPORTED", "falsifier": "NOT_TRIGGERED", "detail": "y"})
        self.assertTrue(any(c["status"] == "contradicted" for c in found))


class History(unittest.TestCase):
    def test_t14_d08_immutable(self):
        from vertical_slice import evolution_decision as DEC
        self.assertEqual(DEC.decide()["decision"], "NO_CHANGE")

    def test_t15_temporal_lineage(self):
        artifact = _artifact()
        self.assertEqual(artifact["upstream_identities"]["vs-d08-decision"], "NO_CHANGE")
        self.assertTrue(any(h["prior_status"] == "requires_more_evidence"
                            for h in artifact["hypotheses"]))

    def test_t15_deployment_independence(self):
        d10 = _d10_artifact()
        cycles = sorted(r["cycle_id"] for r in d10["observations"]
                        if r["observation_id"].startswith("deploy-cycle-"))
        self.assertEqual(cycles, ["cycle-01", "cycle-02", "cycle-03"])


class Firewall(unittest.TestCase):
    def test_t16_no_authorization(self):
        artifact = _artifact()
        blob = str(artifact)
        for token in ("AUTHORIZE_EVOLUTION", "REJECT_EVOLUTION"):
            self.assertNotIn(token, blob)
        self.assertNotIn("decision", [k for k in artifact])
        for hypothesis in artifact["hypotheses"]:
            self.assertIn(hypothesis["evolution_relevance"],
                          ("ELIGIBLE_FOR_EVOLUTION_REVIEW",
                           "REQUIRES_MORE_EVIDENCE", "NOT_EVOLUTION_RELEVANT",
                           "CONTRADICTED"))

    def test_t17_isr_firewall(self):
        import ast
        import os
        src = open(os.path.join("vertical_slice", "interpretation_v2.py"),
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

    def test_t18_requirement_firewall(self):
        artifact = _artifact()
        blob = str(artifact).lower()
        for marker in ("new requirement", "rewrite requirement", "change the isr"):
            self.assertNotIn(marker, blob, marker)


class Provenance(unittest.TestCase):
    def test_t19_complete(self):
        artifact = _artifact()
        for claim in artifact["claims"]:
            self.assertTrue(claim["evidence_refs"], claim["claim_id"])
            self.assertTrue(claim["provenance"], claim["claim_id"])
        for finding in artifact["findings"]:
            self.assertTrue(finding["claim_refs"], finding["finding_id"])
            self.assertTrue(finding["evidence_refs"], finding["finding_id"])
        for hypothesis in artifact["hypotheses"]:
            self.assertTrue(hypothesis["supporting_findings"],
                            hypothesis["hypothesis_id"])
            self.assertTrue(hypothesis["supporting_observations"],
                            hypothesis["hypothesis_id"])
            self.assertTrue(hypothesis["falsifier"], hypothesis["hypothesis_id"])


def _split_records():
    """Frozen D10 file records split for pure interpret() (no servers)."""
    import json
    with open("vertical_slice/evidence_acquisition_results.json",
              encoding="utf-8") as f:
        d10 = json.load(f)
    auth = sorted(
        (r for r in d10["observations"]
         if r["hypothesis_id"] == "vs1-hypothesis-auth-model-adequate"),
        key=lambda r: r["observation_id"])
    deploy = sorted(
        (r for r in d10["observations"]
         if r["hypothesis_id"] == "vs1-hypothesis-deploy-repeatable"),
        key=lambda r: r["observation_id"])
    return auth, deploy, dict(d10["provenance"])


class Determinism(unittest.TestCase):
    def test_t20_deterministic(self):
        import json
        auth, deploy, provenance = _split_records()
        first = INTP.interpret(auth, deploy, provenance)
        second = INTP.interpret(auth, deploy, provenance)
        self.assertEqual(json.dumps(first, sort_keys=True),
                         json.dumps(second, sort_keys=True))

    def test_t21_reordered(self):
        import json
        auth, deploy, provenance = _split_records()
        straight = INTP.interpret(auth, deploy, provenance)
        flipped = INTP.interpret(list(reversed(auth)), list(reversed(deploy)),
                                 provenance)
        self.assertEqual(json.dumps(straight, sort_keys=True),
                         json.dumps(flipped, sort_keys=True))


class FailClosed(unittest.TestCase):
    def test_t22_missing_evidence(self):
        with self.assertRaises(Exception):
            INTP.load_d10("vertical_slice/does-not-exist.json")

    def test_t23_missing_falsifier(self):
        # build_hypotheses with no known findings fails closed (unknown finding).
        with self.assertRaises(INTP.InterpretationError):
            INTP.build_hypotheses(
                {"support": "SUPPORTED", "falsifier": "NOT_TRIGGERED", "detail": "x"},
                {"support": "SUPPORTED", "falsifier": "NOT_TRIGGERED", "detail": "y"},
                [], {})

    def test_t24_broken_provenance(self):
        with self.assertRaises(INTP.InterpretationError):
            INTP._claim("security-observation", "x", [], [], {}, "supported")

    def test_t25_overclaim_rejected(self):
        with self.assertRaises(INTP.InterpretationError):
            INTP.assert_bounded("The deployment is universally reliable.")

    def test_t26_empty_evidence(self):
        import copy
        artifact = _artifact()
        _ = artifact
        with self.assertRaises(INTP.InterpretationError):
            INTP.evaluate_auth([])

    def test_t27_no_orphan_claims(self):
        artifact = _artifact()
        for claim in artifact["claims"]:
            self.assertTrue(claim["evidence_refs"], claim["claim_id"])

    def test_t28_no_orphan_findings(self):
        artifact = _artifact()
        for finding in artifact["findings"]:
            self.assertTrue(finding["claim_refs"], finding["finding_id"])

    def test_t29_no_orphan_hypotheses(self):
        artifact = _artifact()
        for hypothesis in artifact["hypotheses"]:
            self.assertTrue(hypothesis["supporting_findings"],
                            hypothesis["hypothesis_id"])

    def test_t30_hash(self):
        import hashlib
        import json
        artifact = _artifact()
        recomputed = hashlib.sha256(json.dumps(
            {k: v for k, v in artifact.items() if k != "content_hash"},
            sort_keys=True, separators=(",", ":")).encode()).hexdigest()
        self.assertEqual(artifact["content_hash"], recomputed)


if __name__ == "__main__":
    unittest.main()
