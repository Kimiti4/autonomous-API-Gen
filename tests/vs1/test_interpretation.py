"""VS-D07 tests T01-T28: interpretation + epistemic structuring (facts only)."""
from __future__ import annotations

import unittest

from vertical_slice import interpretation as INTP


class FrozenIdentities(unittest.TestCase):
    def test_t01_d01(self):
        self.assertEqual(
            INTP.upstream_identities()["vs-d01-graph-sha256"],
            "28548494e754e9b8214e9f72511a7ba0187fa3378264306a82ff8868bd2e5526")

    def test_t02_d02(self):
        self.assertEqual(
            INTP.upstream_identities()["vs-d02-isr-content-hash"],
            "48e53dcef47aad84e52e20ec116f5b1f9616a626f42d1c281e3cc26cdf8e9dfb")

    def test_t03_d03(self):
        self.assertEqual(INTP.upstream_identities()["vs-d03-selected"], "vs1-candidate-a")

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

    def test_t06_d06_contract(self):
        from vertical_slice import observation as OBS
        self.assertEqual(OBS.OBSERVATION_CONTRACT_VERSION, "vs1-observe-v1")


class EvidenceLoading(unittest.TestCase):
    def test_t07_schema(self):
        evidence = INTP.load_evidence()
        self.assertEqual(len(evidence["records"]), 7)

    def test_t08_provenance(self):
        evidence = INTP.load_evidence()
        for record in evidence["records"]:
            for field in ("observation_contract", "deployment_id",
                          "implementation_id", "vs-d01-graph-sha256",
                          "vs-d02-isr-content-hash", "vs-d03-selected"):
                self.assertIn(field, record["provenance"])


class Separation(unittest.TestCase):
    def _built(self):
        evidence = INTP.load_evidence()
        from vertical_slice import observation as OBS
        records = OBS.normalize(evidence["records"])
        provenance = dict(records[0]["provenance"])
        claims = INTP.build_claims(records, provenance)
        findings = INTP.build_findings(claims, provenance)
        hypotheses = INTP.build_hypotheses(findings, provenance)
        return records, claims, findings, hypotheses

    def test_t09_separation(self):
        records, claims, findings, hypotheses = self._built()
        record_ids = {r["observation_id"] for r in records}
        for claim in claims:
            self.assertTrue(set(claim["supporting_observations"]) <= record_ids)
            self.assertNotIn("hypothesis", claim["claim_type"])
        for hypothesis in hypotheses:
            self.assertTrue(hypothesis["supporting_findings"])

    def test_t10_claim_lineage(self):
        _, claims, _, _ = self._built()
        for claim in claims:
            self.assertTrue(claim["supporting_observations"], claim["claim_id"])
            self.assertTrue(claim["provenance"])

    def test_t11_finding_lineage(self):
        _, claims, findings, _ = self._built()
        claim_ids = {c["claim_id"] for c in claims}
        for finding in findings:
            self.assertTrue(set(finding["supporting_claims"]) <= claim_ids)
            self.assertTrue(finding["supporting_observations"])

    def test_t12_hypotheses(self):
        _, _, findings, hypotheses = self._built()
        self.assertGreaterEqual(len(hypotheses), 1)
        for hypothesis in hypotheses:
            self.assertTrue(hypothesis["supporting_findings"])
            self.assertTrue(hypothesis["falsifiers"])
            self.assertEqual(hypothesis["status"], "proposed")

    def test_t13_falsifiers(self):
        _, _, _, hypotheses = self._built()
        for hypothesis in hypotheses:
            self.assertTrue(hypothesis["falsifiers"], hypothesis["hypothesis_id"])
            self.assertTrue(hypothesis["acceptance_conditions"])

    def test_t14_scope(self):
        _, claims, findings, _ = self._built()
        blob = str(claims + findings).lower()
        for overclaim in ("production reliability", "always available",
                          "optimal architecture"):
            self.assertNotIn(overclaim, blob)
        boundary = [c for c in claims if c["claim_type"] == "boundary-condition"]
        self.assertTrue(boundary)

    def test_t15_uncertainty(self):
        _, claims, _, _ = self._built()
        uncertain = [c for c in claims if c["claim_type"] == "uncertainty"]
        self.assertTrue(uncertain)
        for claim in uncertain:
            self.assertIn(claim["status"], ("supported", "weakly_supported",
                                            "undetermined"))

    def test_t16_contradictions(self):
        evidence = INTP.load_evidence()
        from vertical_slice import observation as OBS
        records = OBS.normalize(evidence["records"])
        contradictions = INTP.detect_contradictions(records, [])
        self.assertEqual(contradictions, [])
        # ...but the detector fires on genuinely conflicting input:
        dup = [dict(records[0]), dict(records[0])]
        dup[1] = dict(dup[1], result="conflicting-result")
        found = INTP.detect_contradictions(dup, [])
        self.assertEqual(len(found), 1)
        self.assertEqual(found[0]["status"], "contradicted")

    def test_t17_negative_evidence(self):
        _, claims, _, _ = self._built()
        neg = [c for c in claims if c["claim_type"] == "uncertainty"]
        self.assertTrue(any("absence" in c["statement"].lower() for c in neg))

    def test_t18_eligibility(self):
        _, _, _, hypotheses = self._built()
        allowed = {"eligible_for_evolution_review", "requires_more_evidence",
                   "insufficient_evidence", "contradicted", "out_of_scope"}
        for hypothesis in hypotheses:
            self.assertIn(hypothesis["evolution_eligibility"], allowed)


class Immutability(unittest.TestCase):
    def test_t19_isr_immutable(self):
        from vertical_slice.isr import build_task_tracker_isr
        rev = build_task_tracker_isr()
        self.assertEqual(rev.content_hash,
                         "48e53dcef47aad84e52e20ec116f5b1f9616a626f42d1c281e3cc26cdf8e9dfb")
        INTP.build_interpretation_evidence()
        self.assertEqual(build_task_tracker_isr(), rev)


class Determinism(unittest.TestCase):
    def test_t20_normalization(self):
        first = INTP.build_interpretation_evidence()
        second = INTP.build_interpretation_evidence()
        self.assertEqual(first, second)

    def test_t21_equivalence(self):
        import json
        first = json.dumps(INTP.build_interpretation_evidence(), sort_keys=True)
        second = json.dumps(INTP.build_interpretation_evidence(), sort_keys=True)
        self.assertEqual(first, second)


class Safety(unittest.TestCase):
    def test_t22_redaction(self):
        artifact = INTP.build_interpretation_evidence()
        blob = __import__("json").dumps(artifact).lower()
        for marker in ("alice-secret", "bob-secret", "cara-secret", "eve-secret",
                       "vs1-test-token", "vs1-deploy-token", "vs1-obs-token",
                       "password"):
            self.assertNotIn(marker, blob, marker)

    def test_t23_invalid_evidence(self):
        with self.assertRaises(Exception):
            INTP.load_evidence("vertical_slice/does-not-exist.json")

    def test_t24_missing_provenance(self):
        evidence = INTP.load_evidence()
        from vertical_slice import observation as OBS
        records = OBS.normalize(evidence["records"])
        broken = dict(records[0])
        broken["provenance"] = {"observation_contract": "vs1-observe-v1"}
        with self.assertRaises(OBS.ObservationError):
            OBS.normalize([broken])

    def test_t25_unsupported_claim(self):
        with self.assertRaises(INTP.InterpretationError):
            INTP._claim("oracle-prophecy", "x", ["P01-001"],
                        {"observation_contract": "vs1-observe-v1"}, "supported")

    def test_t26_missing_falsifier(self):
        with self.assertRaises(INTP.InterpretationError):
            from vertical_slice import observation as OBS  # noqa: F401
            INTP.build_hypotheses([], {})


class Firewall(unittest.TestCase):
    def test_t27_evolution_firewall(self):
        import ast
        import os
        src = open(os.path.join("vertical_slice", "interpretation.py"),
                   encoding="utf-8").read()
        tree = ast.parse(src)
        identifiers: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Name):
                identifiers.add(node.id.lower())
            elif isinstance(node, ast.Attribute):
                identifiers.add(node.attr.lower())
        for token in ("mutate", "crossover", "select_candidate", "deploy",
                      "uvicorn", "docker", "retire", "migrate"):
            self.assertNotIn(token, identifiers, token)

    def test_t28_implementation_immutable(self):
        from vertical_slice import implementation as IMPL
        before = IMPL.build_evidence()
        INTP.build_interpretation_evidence()
        self.assertEqual(IMPL.build_evidence(), before)


if __name__ == "__main__":
    unittest.main()
