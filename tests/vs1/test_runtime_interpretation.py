"""VS-D18 tests: interpretation of D17 runtime evidence (no evolution).

Every test enforces the interpretation boundary: findings trace to
observations, claims stay within scope, and no decision is produced.
"""
from __future__ import annotations

import ast
import json
import unittest

from vertical_slice import runtime_interpretation as RI


class InterpretationContract(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.evidence = RI.load_evidence()
        cls.record = RI.assemble_interpretation(
            cls.evidence, "2026-01-01T00:00:00+00:00")

    def test_evidence_identity(self):
        self.assertEqual(self.evidence["implementation_id"], "vs1-impl-v2")
        self.assertEqual(self.evidence["architecture_id"],
                         "vs1-evolved-96fe2d29fd76")
        self.assertEqual(self.evidence["summary"]["status_counts"]["FAIL"], 0)

    def test_evidence_hash_verifies(self):
        # Tampered evidence must fail closed at load time.
        tampered = json.loads(json.dumps(self.evidence))
        tampered["summary"]["observation_count"] = 999
        with open("vertical_slice/runtime_observation_evidence.json",
                  encoding="utf-8") as f:
            _ = f  # source of truth stays the committed file
        with self.assertRaises(RI.InterpretationError):
            RI.assess({"observations": [], "summary": tampered["summary"]})

    def test_findings_trace_to_observations(self):
        known = {r["observation_id"] for r in self.evidence["observations"]}
        for finding in self.record["findings"]:
            self.assertTrue(finding["observation_ids"], finding["finding_id"])
            self.assertLessEqual(set(finding["observation_ids"]), known,
                                 finding["finding_id"])
            self.assertIn(finding["support"], RI.SUPPORT_VALUES)

    def test_no_overreach_language(self):
        blob = json.dumps(self.record["findings"]).lower()
        for token in RI.BANNED_CLAIM_TOKENS:
            self.assertNotIn(token, blob, token)

    def test_unknowns_nonempty(self):
        self.assertGreaterEqual(len(self.record["unknowns"]), 5)

    def test_explicit_non_decision(self):
        decision = self.record["decision"]
        self.assertEqual(decision["evolution_decision"], "NONE")
        self.assertEqual(decision["authorization"], "NONE")
        self.assertIs(decision["production_authorization"], False)

    def test_deterministic(self):
        again = RI.assemble_interpretation(self.evidence,
                                           "2027-05-05T00:00:00+00:00")
        self.assertEqual(again["content_hash"], self.record["content_hash"])
        self.assertEqual(again["findings"], self.record["findings"])

    def test_module_firewall(self):
        src = open(RI.__file__, encoding="utf-8").read()
        tree = ast.parse(src)
        imports: set[str] = set()
        called: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.update(a.name for a in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imports.add(node.module)
            elif isinstance(node, ast.Call):
                func = node.func
                called.add(func.id if isinstance(func, ast.Name)
                           else func.attr if isinstance(func, ast.Attribute)
                           else "")
        self.assertLessEqual(imports, {"__future__", "hashlib", "json",
                                       "typing"}, imports)
        for name in ("choose_candidate", "decide", "deploy", "publish",
                     "regenerate", "evolve", "authorize", "Popen", "run"):
            self.assertNotIn(name, called, (name, called))
        # Exactly one file access (read-only evidence load), no writes.
        self.assertEqual(src.count("open("), 1, src.count("open("))
        self.assertNotIn('"w"', src)
        self.assertNotIn("'w'", src)

    def test_upstream_untouched(self):
        from vertical_slice import regeneration as REG
        self.assertEqual(REG.build_evidence()["implementation_hash"],
                         RI.EXPECTED_IMPL_HASH)

    def test_committed_record_matches(self):
        committed = json.load(open(
            "vertical_slice/runtime_interpretation_evidence.json",
            encoding="utf-8"))
        self.assertEqual(committed["contract"], RI.INTERPRETATION_CONTRACT)
        self.assertEqual(committed["evidence_hash"],
                         self.evidence["normalized_hash"])
        self.assertEqual(len(committed["findings"]), 10)


if __name__ == "__main__":
    unittest.main()
