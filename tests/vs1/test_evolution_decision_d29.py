"""VS-D29 tests: evidence-sufficiency decision (definition, never execution).

Static suite. Tamper tests redirect module path constants at temp copies;
upstream files are byte-compared, never written.
"""
from __future__ import annotations

import ast
import copy
import hashlib
import json
import tempfile
import os
import unittest
from unittest import mock

from vertical_slice import evolution_decision_d29 as D29

D28_PATH = "vertical_slice/runtime_interpretation_d28_evidence.json"
D29_EVIDENCE = "vertical_slice/evolution_decision_d29_evidence.json"
CLASSIFICATIONS = {"CERTIFIED", "QUALIFIED_PARTIAL", "SUPPORTED",
                   "HYPOTHESIZED", "UNKNOWN", "PENDING", "BLOCKED", "REJECTED"}


def _sha_file(path: str) -> str:
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def _temp_copy(path: str, mutate):
    tmp = tempfile.NamedTemporaryFile(
        mode="w", suffix=".json", delete=False, encoding="utf-8")
    record = json.load(open(path, encoding="utf-8"))
    mutate(record)
    tmp.write(json.dumps(record))
    tmp.close()
    return tmp.name


class Upstream(unittest.TestCase):
    def test_d28_resolves(self):
        inputs = D29.verify_upstream()
        self.assertEqual(inputs["d28"]["interpretation_id"],
                         "vs1-d28-interp-52a8906c3187b244")

    def test_coverage_matches_authoritative(self):
        d28 = json.load(open(D28_PATH, encoding="utf-8"))
        coverage = {item["criterion_id"]: item["status"]
                    for item in d28["requirement_coverage"]}
        self.assertEqual(coverage, D29.EXPECTED_COVERAGE)
        # Authoritative map, not the prompt example's: update observed.
        self.assertEqual(coverage["SC03"], "OBSERVED")
        self.assertEqual(coverage["SC05"], "OBSERVED")

    def test_lineage_hashes(self):
        inputs = D29.verify_upstream()
        self.assertEqual(inputs["d28"]["source_evidence_hash"],
                         inputs["d27"]["normalized_hash"])
        self.assertEqual(inputs["d28"]["isr_hash"], D29.EXPECTED_ISR)

    def test_tampered_d28_fails_closed(self):
        bad = _temp_copy(D28_PATH, lambda r: r["requirement_coverage"].__setitem__(
            0, dict(r["requirement_coverage"][0], status="OBSERVED")))
        self.addCleanup(lambda: os.unlink(bad))
        with mock.patch.object(D29, "D28_PATH", bad):
            with self.assertRaises(D29.DecisionError):
                D29.verify_upstream()

    def test_missing_provenance_fails_closed(self):
        bad = _temp_copy(D28_PATH, lambda r: r.pop("isr_hash"))
        self.addCleanup(lambda: os.unlink(bad))
        with mock.patch.object(D29, "D28_PATH", bad):
            with self.assertRaises(D29.DecisionError):
                D29.verify_upstream()


class Capabilities(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.d28 = json.load(open(D28_PATH, encoding="utf-8"))
        cls.coverage = {item["criterion_id"]: item["status"]
                        for item in cls.d28["requirement_coverage"]}
        cls.caps = {c["id"]: c for c in D29.capability_table()}

    def test_ten_capabilities(self):
        self.assertEqual(len(self.caps), 10)

    def test_unknown_never_advances(self):
        for cap in self.caps.values():
            sc_statuses = {self.coverage.get(sc, "UNKNOWN") for sc in cap["sc"]}
            if "UNKNOWN" in sc_statuses or "INSUFFICIENT" in sc_statuses:
                self.assertIn(cap["decision"], ("HOLD", "BLOCK"), cap["id"])

    def test_production_blocked(self):
        self.assertEqual(self.caps["CAP-008"]["decision"], "BLOCK")

    def test_autonomy_blocked(self):
        self.assertEqual(self.caps["CAP-009"]["decision"], "BLOCK")

    def test_chain_retained(self):
        self.assertEqual(self.caps["CAP-010"]["decision"], "RETAIN")
        self.assertEqual(self.caps["CAP-006"]["decision"], "RETAIN")

    def test_cap001_bounded(self):
        cap = self.caps["CAP-001"]
        self.assertEqual(cap["decision"], "HOLD")
        # Production may appear only as excluded scope, never as granted.
        blob = (cap["rationale"] + " " + cap["next"]).lower()
        self.assertNotIn("production granted", blob)
        self.assertNotIn("production authorized", blob)
        self.assertNotIn("production-ready", blob)


class EvolutionDecisions(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.evs = {e["id"]: e for e in D29.evolution_decisions()}

    def test_ev001_hold(self):
        self.assertEqual(self.evs["EV-001"]["decision"], "HOLD")

    def test_ev002_advance_definition_only(self):
        self.assertEqual(self.evs["EV-002"]["decision"], "ADVANCE")
        self.assertEqual(self.evs["EV-002"]["class"], "E1")

    def test_ev003_hold(self):
        self.assertEqual(self.evs["EV-003"]["decision"], "HOLD")

    def test_ev004_block(self):
        self.assertEqual(self.evs["EV-004"]["decision"], "BLOCK")

    def test_ev005_block(self):
        self.assertEqual(self.evs["EV-005"]["decision"], "BLOCK")

    def test_ev006_retain(self):
        self.assertEqual(self.evs["EV-006"]["decision"], "RETAIN")

    def test_no_execution_authority(self):
        blob = json.dumps(self.evs).lower()
        for token in ("authorized to implement", "may deploy",
                      "production granted", "autonomy granted"):
            self.assertNotIn(token, blob, token)


class KnowledgeContradictions(unittest.TestCase):
    def test_ledger_classifications(self):
        for kid, _prop, cls in D29.knowledge_ledger():
            self.assertIn(cls, CLASSIFICATIONS, kid)

    def test_no_upgrade_by_repetition(self):
        by_prop = {}
        for _kid, prop, cls in D29.knowledge_ledger():
            by_prop.setdefault(prop, set()).add(cls)
        for prop, classes in by_prop.items():
            self.assertEqual(len(classes), 1, prop)

    def test_con001_preserved(self):
        registry = D29.contradiction_registry()
        self.assertEqual(len(registry), 1)
        con = registry[0]
        self.assertEqual(con["id"], "CON-001")
        self.assertEqual(con["resolution"], "UNRESOLVED")

    def test_no_fabricated_con002(self):
        registry = D29.contradiction_registry()
        self.assertFalse([c for c in registry if c["id"] == "CON-002"])


class DeterminismFirewall(unittest.TestCase):
    def test_repeat_identical(self):
        first = D29.assemble_evidence("2026-01-01T00:00:00+00:00")
        second = D29.assemble_evidence("2027-05-05T00:00:00+00:00")
        self.assertEqual(first["decision_hash"], second["decision_hash"])

    def test_canonical_file(self):
        raw = open(D29_EVIDENCE, encoding="utf-8").read()
        self.assertEqual(raw, json.dumps(json.loads(raw), sort_keys=True,
                                         separators=(",", ":"),
                                         ensure_ascii=False) + "\n")

    def test_hash_recomputes(self):
        evidence = json.load(open(D29_EVIDENCE, encoding="utf-8"))
        check = {k: v for k, v in evidence.items()
                 if k not in ("provenance", "decision_hash")}
        provenance = dict(evidence["provenance"])
        provenance.pop("generated_at", None)
        check["provenance"] = provenance
        digest = hashlib.sha256(json.dumps(
            check, sort_keys=True, separators=(",", ":"),
            ensure_ascii=False).encode()).hexdigest()
        self.assertEqual(digest, evidence["decision_hash"])

    def test_final_decision(self):
        evidence = json.load(open(D29_EVIDENCE, encoding="utf-8"))
        self.assertEqual(evidence["final_governance_decision"], "PASS / HOLD")
        for key in ("implementation", "deployment", "production",
                    "runtime_execution"):
            self.assertEqual(evidence["authorizations"][key], "NONE", key)

    def test_no_execution_paths(self):
        tree = ast.parse(open(D29.__file__, encoding="utf-8").read())
        called: set[str] = set()
        imports: set[str] = set()
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
        for name in ("Popen", "run", "deploy", "compile", "push", "optimize",
                     "evolve", "urlopen"):
            self.assertNotIn(name, called, (name, called))

    def test_upstream_stable(self):
        paths = [D28_PATH,
                 "vertical_slice/runtime_observation_d27_evidence.json",
                 "vertical_slice/deployment_d26_evidence.json",
                 "vertical_slice/isr.py"]
        before = {p: _sha_file(p) for p in paths}
        D29.assemble_evidence("2026-01-01T00:00:00+00:00")
        self.assertEqual({p: _sha_file(p) for p in paths}, before)


if __name__ == "__main__":
    unittest.main()
