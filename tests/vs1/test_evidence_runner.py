"""VS-D10 tests T01-T26: controlled evidence acquisition (execution only)."""
from __future__ import annotations

import unittest

from vertical_slice import evidence_runner as RUN


class UpstreamIdentities(unittest.TestCase):
    def test_t01_d01(self):
        self.assertEqual(
            RUN.upstream_identities()["vs-d01-graph-sha256"],
            "28548494e754e9b8214e9f72511a7ba0187fa3378264306a82ff8868bd2e5526")

    def test_t02_d02(self):
        self.assertEqual(
            RUN.upstream_identities()["vs-d02-isr-content-hash"],
            "48e53dcef47aad84e52e20ec116f5b1f9616a626f42d1c281e3cc26cdf8e9dfb")

    def test_t03_d03(self):
        self.assertEqual(RUN.upstream_identities()["vs-d03-selected"], "vs1-candidate-a")

    def test_t04_d04(self):
        self.assertEqual(RUN.upstream_identities()["vs-d04-implementation"], "vs1-impl-v1")

    def test_t05_d05(self):
        self.assertEqual(RUN.upstream_identities()["vs-d05-deployment"], "vs1-deploy-v1")

    def test_t06_d06(self):
        self.assertEqual(RUN.upstream_identities()["vs-d06-observation"], "vs1-observe-v1")

    def test_t07_d07(self):
        import json
        evidence = json.load(open("vertical_slice/interpretation_evidence.json"))
        self.assertEqual(len(evidence["hypotheses"]), 3)

    def test_t08_d08(self):
        self.assertEqual(RUN.upstream_identities()["vs-d08-decision"], "NO_CHANGE")

    def test_t09_d09(self):
        self.assertEqual(RUN.upstream_identities()["vs-d09-policy"],
                         "vs1-evidence-acquisition-v1")
        self.assertEqual(RUN.upstream_identities()["vs-d09-outcome"],
                         "EVIDENCE_PLAN_REQUIRED")

    def test_t10_plan_integrity(self):
        plans = RUN.load_plans()
        self.assertEqual(len(plans), 2)
        self.assertEqual(sum(p["observation_count"] for p in plans), 7)


class Execution(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.artifact = RUN.build_artifact(run_id="vs1-d10-test-run")
        by_plan: dict[str, list] = {}
        for record in cls.artifact["observations"]:
            by_plan.setdefault(record["plan_id"], []).append(record)
        cls.by_plan = by_plan

    def test_t11_exact_count(self):
        self.assertEqual(len(self.artifact["observations"]), 7)
        counts = sorted(len(v) for v in self.by_plan.values())
        self.assertEqual(counts, [3, 4])

    def test_t12_no_scope_expansion(self):
        self.assertEqual(self.artifact["summary"]["authorized_observations"], 7)
        self.assertEqual(self.artifact["summary"]["executed_observations"], 7)

    def test_t13_auth_execution(self):
        auth = [r for r in self.artifact["observations"]
                if r["observation_id"].startswith("auth-")]
        self.assertEqual(len(auth), 4)
        for record in auth:
            self.assertIn(record["outcome"], ("PASS", "FAIL", "UNDETERMINED", "BLOCKED"))

    def test_t14_deploy_execution(self):
        deploy = [r for r in self.artifact["observations"]
                  if r["observation_id"].startswith("deploy-cycle-")]
        self.assertEqual(len(deploy), 3)

    def test_t15_independence(self):
        deploy = sorted(
            (r for r in self.artifact["observations"]
             if r["observation_id"].startswith("deploy-cycle-")),
            key=lambda r: r["cycle_id"])
        self.assertEqual([r["cycle_id"] for r in deploy],
                         ["cycle-01", "cycle-02", "cycle-03"])
        stores = [r["normalized_result"]["observed"].get("cycle_store") for r in deploy]
        # isolation audit: each cycle ran against its own store directory
        self.assertEqual(len(set(stores)), 3)

    def test_t16_failure_recording(self):
        self.assertEqual(RUN.classify_observation(201, 500), "FAIL")
        for record in self.artifact["observations"]:
            self.assertIn(record["outcome"], ("PASS", "FAIL", "UNDETERMINED", "BLOCKED"))

    def test_t17_undetermined(self):
        self.assertEqual(RUN.classify_observation(200, None), "UNDETERMINED")

    def test_t18_blocked(self):
        self.assertEqual(RUN.classify_observation(200, 200, executable=False), "BLOCKED")


class Safety(unittest.TestCase):
    def test_t19_secret_protection(self):
        # Per the authorization (§13): secret-VALUE shapes are forbidden;
        # ordinary discussion terms (password, token, credential, redaction)
        # in plan prose are explicitly allowed.
        import json
        import re
        blob = json.dumps(self._artifact())
        self.assertIsNone(re.search(
            r"(password|passwd|secret|api_key|session_cookie|private_key"
            r"|credential)\s*[:=]\s*\S+", blob, re.IGNORECASE))
        for marker in ("alice-secret-pw", "bob-secret-pw", "cara-secret-pw",
                       "vs1-test-token", "vs1-deploy-token", "vs1-obs-token",
                       "vs1-d10-token"):
            self.assertNotIn(marker, blob.lower(), marker)

    def _artifact(self):
        if not hasattr(self, "_cached"):
            self._cached = RUN.build_artifact(run_id="vs1-d10-secret-scan")
        return self._cached

    def test_t20_security_preservation(self):
        self.assertEqual(RUN.upstream_identities()["vs-d04-implementation"], "vs1-impl-v1")


class Lineage(unittest.TestCase):
    def test_t21_provenance(self):
        artifact = RUN.build_artifact(run_id="vs1-d10-prov-check")
        for record in artifact["observations"]:
            for field in ("vs-d01-graph-sha256", "vs-d02-isr-content-hash",
                          "vs-d03-selected", "vs-d09-policy"):
                self.assertIn(field, record["provenance"], (record["observation_id"], field))

    def test_t22_normalization(self):
        first = RUN.build_artifact(run_id="vs1-d10-norm")
        # Re-normalizing the same records is byte-stable.
        again = RUN.normalize_evidence(first["observations"])
        self.assertEqual(
            [r["evidence_id"] for r in again],
            [r["evidence_id"] for r in first["observations"]])
        keys = [(r["plan_id"], r["observation_id"], r["run_id"], r["cycle_id"])
                for r in again]
        self.assertEqual(keys, sorted(keys))


class Firewall(unittest.TestCase):
    def test_t23_no_interpretation(self):
        import ast
        import os
        src = open(os.path.join("vertical_slice", "evidence_runner.py"),
                   encoding="utf-8").read()
        tree = ast.parse(src)
        identifiers: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Name):
                identifiers.add(node.id.lower())
            elif isinstance(node, ast.Attribute):
                identifiers.add(node.attr.lower())
        for token in ("adequate", "sufficient", "proven", "repeatable",
                      "recommend", "hypothesis_supported", "hypothesis_falsified"):
            self.assertNotIn(token, identifiers, token)
        artifact = RUN.build_artifact(run_id="vs1-d10-firewall")
        blob = str(artifact).lower()
        for phrase in ("hypothesis supported", "hypothesis falsified",
                       "architecture adequate", "evolution required",
                       "proven repeatable"):
            self.assertNotIn(phrase, blob, phrase)

    def test_t24_evolution_firewall(self):
        artifact = RUN.build_artifact(run_id="vs1-d10-evol-check")
        # The artifact carries the consumed D08 decision as provenance; it
        # must not emit a decision of its own.
        self.assertNotIn("decision", artifact)
        self.assertNotIn("decision_rationale", artifact)
        for key in ("AUTHORIZE_EVOLUTION", "REJECT_EVOLUTION"):
            self.assertNotIn(key, str(artifact))
        import ast
        import os
        src = open(os.path.join("vertical_slice", "evidence_runner.py"),
                   encoding="utf-8").read()
        tree = ast.parse(src)
        identifiers = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Name):
                identifiers.add(node.id)
            elif isinstance(node, ast.Attribute):
                identifiers.add(node.attr)
        # NOTE: stdlib re.compile is allowed; compiler *authority* is not.
        for token in ("AUTHORIZE_EVOLUTION", "authorize_evolution",
                      "mutate", "crossover", "compiler", "compilation",
                      "isr_to_plan", "deploy", "uvicorn",
                      "docker", "retire", "migrate", "patch", "rewrite"):
            self.assertNotIn(token, identifiers, token)

    def test_t25_upstream_unchanged(self):
        RUN.build_artifact(run_id="vs1-d10-upstream-check")
        identities = RUN.upstream_identities()
        self.assertEqual(identities["vs-d03-selected"], "vs1-candidate-a")
        self.assertEqual(
            identities["vs-d01-graph-sha256"],
            "28548494e754e9b8214e9f72511a7ba0187fa3378264306a82ff8868bd2e5526")

    def test_t26_artifact_integrity(self):
        import hashlib
        import json
        artifact = RUN.build_artifact(run_id="vs1-d10-integrity")
        recomputed = hashlib.sha256(json.dumps(
            {k: v for k, v in artifact.items() if k != "content_hash"},
            sort_keys=True, separators=(",", ":")).encode()).hexdigest()
        self.assertEqual(artifact["content_hash"], recomputed)
        self.assertEqual(len(RUN.normalize_evidence(artifact["observations"])),
                         len(artifact["observations"]))


if __name__ == "__main__":
    unittest.main()
