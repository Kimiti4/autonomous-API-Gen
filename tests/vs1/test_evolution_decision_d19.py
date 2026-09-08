"""VS-D19 tests T01-T35: evolution decision gate (decision, never authorization).

Static suite: D19 performs no launches, no mutation, no I/O beyond reading
the frozen input artifacts. Tamper tests operate on temp copies only.
"""
from __future__ import annotations

import ast
import hashlib
import json
import os
import tempfile
import unittest

from vertical_slice import evolution_decision_d19 as D19

D18_PATH = "vertical_slice/runtime_interpretation_evidence.json"
D17_PATH = "vertical_slice/runtime_observation_evidence.json"
D12_PATH = "vertical_slice/evolution_decision_v2_evidence.json"
D19_EVIDENCE = "vertical_slice/evolution_decision_d19_evidence.json"


def _sha_file(path: str) -> str:
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


class Inputs(unittest.TestCase):
    def test_t01_d18_resolves(self):
        record = D19._load_json(D18_PATH)
        self.assertEqual(record.get("contract"), "vs1-runtime-interpret-v1")

    def test_t02_d18_hash_verifies(self):
        inputs = D19.verify_inputs()
        self.assertEqual(inputs["d18_hash"], inputs["d18"]["content_hash"])

    def test_t03_d17_identity_verifies(self):
        inputs = D19.verify_inputs()
        self.assertEqual(inputs["d18"]["evidence_hash"],
                         inputs["d17"]["normalized_hash"])
        self.assertEqual(inputs["d17"]["execution_id"], "vs1-d17-run-001")

    def test_t04_d12_resolves(self):
        inputs = D19.verify_inputs()
        self.assertEqual(inputs["d12"]["decision"], "NO_CHANGE")

    def test_t05_d12_no_change(self):
        with open(D12_PATH, encoding="utf-8") as f:
            self.assertEqual(json.load(f).get("decision"), "NO_CHANGE")

    def test_t06_real_authorization_zero(self):
        evidence = json.load(open(D19_EVIDENCE, encoding="utf-8"))
        self.assertEqual(evidence["d12_authorization"], 0)
        self.assertEqual(evidence["authorization"], "NONE")
        self.assertEqual(evidence["evolution_authorization"], "NONE")

    def test_t07_production_false(self):
        evidence = json.load(open(D19_EVIDENCE, encoding="utf-8"))
        self.assertIs(evidence["production_authorization"], False)


class FindingsPreservation(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.inputs = D19.verify_inputs()
        cls.d18 = cls.inputs["d18"]
        cls.d17 = cls.inputs["d17"]

    def test_t08_findings_resolve(self):
        ids = [f["finding_id"] for f in self.d18["findings"]]
        self.assertEqual(ids, [f"F{i}" for i in range(1, 11)])

    def test_t09_observation_lineage(self):
        known = {r["observation_id"] for r in self.d17["observations"]}
        for finding in self.d18["findings"]:
            self.assertTrue(finding["observation_ids"])
            self.assertLessEqual(set(finding["observation_ids"]), known)

    def test_t10_unknowns_preserved(self):
        evidence = json.load(open(D19_EVIDENCE, encoding="utf-8"))
        self.assertEqual(evidence["unknowns_considered"],
                         f"{len(self.d18['unknowns'])}/{len(self.d18['unknowns'])}")
        self.assertEqual(len(self.d18["unknowns"]), 7)

    def test_t11_scope_preserved(self):
        for finding in self.d18["findings"]:
            self.assertTrue(finding["scope"].strip(), finding["finding_id"])

    def test_t12_nonfinding_preserved(self):
        f8 = next(f for f in self.d18["findings"] if f["finding_id"] == "F8")
        material = D19.materiality(f8)
        self.assertIs(material["M7_not_measurement_only"], False)
        self.assertEqual(D19.classify(f8), "NO_ACTION")


class Determinism(unittest.TestCase):
    def test_t13_deterministic(self):
        self.assertEqual(D19.decide(), D19.decide())

    def test_t14_byte_identical(self):
        first = D19.assemble_evidence("2026-01-01T00:00:00+00:00")
        second = D19.assemble_evidence("2027-05-05T00:00:00+00:00")
        self.assertEqual(first["decision_hash"], second["decision_hash"])
        self.assertEqual(
            json.dumps(first, sort_keys=True), json.dumps(second, sort_keys=True)
            .replace("2027-05-05T00:00:00+00:00", "2026-01-01T00:00:00+00:00"))

    def test_t15_canonical(self):
        raw = open(D19_EVIDENCE, encoding="utf-8").read()
        self.assertEqual(raw, json.dumps(json.loads(raw), sort_keys=True,
                                         separators=(",", ":"),
                                         ensure_ascii=False) + "\n")

    def test_t16_hash_reproducible(self):
        evidence = json.load(open(D19_EVIDENCE, encoding="utf-8"))
        check = {k: v for k, v in evidence.items()
                 if k not in ("provenance", "decision_hash")}
        provenance = dict(evidence["provenance"])
        provenance.pop("generated_at", None)
        check["provenance"] = provenance
        digest = hashlib.sha256(json.dumps(
            check, sort_keys=True, separators=(",", ":"),
            ensure_ascii=False).encode()).hexdigest()
        self.assertEqual(digest, evidence["decision_hash"])


class NonMutation(unittest.TestCase):
    def test_t17_d12_unchanged(self):
        before = _sha_file(D12_PATH)
        D19.decide()
        D19.assemble_evidence("2026-01-01T00:00:00+00:00")
        self.assertEqual(_sha_file(D12_PATH), before)

    def test_t18_isr_unchanged(self):
        from vertical_slice import implementation as IMPL
        self.assertEqual(
            IMPL.frozen_input_identity()["vs-d02-isr-content-hash"],
            D19.EXPECTED_ISR)

    def test_t19_d17_unchanged(self):
        before = _sha_file(D17_PATH)
        D19.decide()
        self.assertEqual(_sha_file(D17_PATH), before)

    def test_t20_d18_unchanged(self):
        before = _sha_file(D18_PATH)
        D19.decide()
        D19.assemble_evidence("2026-01-01T00:00:00+00:00")
        self.assertEqual(_sha_file(D18_PATH), before)


class NoExecution(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        src = open(D19.__file__, encoding="utf-8").read()
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

    def test_t21_no_candidate_generation(self):
        self.assertLessEqual(
            self.imports, {"__future__", "hashlib", "json", "re", "typing",
                           "vertical_slice"}, self.imports)
        for name in ("generate", "candidates", "propose_architecture"):
            self.assertNotIn(name, self.called, (name, self.called))

    def test_t22_no_architecture_selection(self):
        for name in ("choose_candidate", "select", "rank"):
            self.assertNotIn(name, self.called, (name, self.called))

    def test_t23_no_architecture_mutation(self):
        for name in ("mutate", "retire", "crossover", "optimize"):
            self.assertNotIn(name, self.called, (name, self.called))
        for guard in ("vertical_slice/candidates.py",
                      "vertical_slice/evolution_selection",
                      "vertical_slice/regeneration.py"):
            self.assertNotIn(guard, self.src, guard)

    def test_t24_no_implementation(self):
        for name in ("compile", "emit", "render", "write_text"):
            self.assertNotIn(name, self.called, (name, self.called))
        self.assertNotIn("vertical_slice/app_v2/", self.src)

    def test_t25_no_deployment(self):
        for name in ("Popen", "run", "deploy", "uvicorn", "serve"):
            self.assertNotIn(name, self.called, (name, self.called))

    def test_t26_no_production_authorization(self):
        evidence = json.load(open(D19_EVIDENCE, encoding="utf-8"))
        self.assertIs(evidence["production_authorization"], False)
        self.assertNotIn("production_authorization = True", self.src)
        self.assertNotIn("production_authorization=True", self.src)

    def test_t27_no_push(self):
        self.assertNotIn("subprocess", self.imports | self.called)
        for token in ("git push", "git commit", "PUSH"):
            self.assertNotIn(token, self.src, token)


class FailClosed(unittest.TestCase):
    def _copy(self, path: str, mutate) -> str:
        tmp = tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False, encoding="utf-8")
        record = json.load(open(path, encoding="utf-8"))
        mutate(record)
        tmp.write(json.dumps(record))
        tmp.close()
        self.addCleanup(lambda: os.unlink(tmp.name))
        return tmp.name

    def test_t28_tampered_d18(self):
        tampered = self._copy(
            D18_PATH, lambda r: r["findings"].__setitem__(
                0, dict(r["findings"][0], support="CONTRADICTED")))
        with self.assertRaises(D19.DecisionError):
            D19.verify_inputs(d18_path=tampered)

    def test_t29_malformed_input(self):
        broken = self._copy(D18_PATH, lambda r: r.pop("findings"))
        with self.assertRaises(D19.DecisionError):
            D19.verify_inputs(d18_path=broken)
        missing = self._copy(D18_PATH, lambda r: r.pop("content_hash"))
        with self.assertRaises(D19.DecisionError):
            D19.verify_inputs(d18_path=missing)

    def test_t30_unknown_not_promoted(self):
        finding = {"finding_id": "UX", "support": "UNKNOWN",
                   "claim": "Something might be off.",
                   "scope": "Unbounded.", "observation_ids": ["lifecycle.readiness"]}
        self.assertIs(D19.materiality(finding)["M1_supported"], False)
        self.assertNotEqual(D19.classify(finding), "EVOLUTION_PROPOSED")

    def test_t31_latency_not_judgment(self):
        f8 = next(f for f in D19.verify_inputs()["d18"]["findings"]
                  if f["finding_id"] == "F8")
        self.assertEqual(D19.classify(f8), "NO_ACTION")
        self.assertNotIn("acceptable", f8["claim"].lower())
        self.assertNotIn("sufficient", f8["claim"].lower())

    def test_t32_bounded_not_universal(self):
        inputs = D19.verify_inputs()
        f4 = next(f for f in inputs["d18"]["findings"] if f["finding_id"] == "F4")
        self.assertEqual(D19.classify(f4), "NO_ACTION")
        self.assertIn("single", f4["scope"].lower())


class Separation(unittest.TestCase):
    def test_t33_decision_not_authorization(self):
        evidence = json.load(open(D19_EVIDENCE, encoding="utf-8"))
        self.assertEqual(evidence["decision"], "NO_ACTION")
        self.assertEqual(evidence["authorization"], "NONE")
        self.assertEqual(evidence["evolution_authorization"], "NONE")
        # The module has no statement that could emit authorization.
        src = open(D19.__file__, encoding="utf-8").read().lower()
        self.assertNotIn("authorization\" = \"granted", src)
        self.assertNotIn("authorization = true", src)

    def test_t34_production_unauthorized(self):
        evidence = json.load(open(D19_EVIDENCE, encoding="utf-8"))
        self.assertIs(evidence["production_authorization"], False)
        with open(D12_PATH, encoding="utf-8") as f:
            self.assertEqual(json.load(f).get("decision"), "NO_CHANGE")

    def test_t35_lineage_resolves(self):
        evidence = json.load(open(D19_EVIDENCE, encoding="utf-8"))
        d18 = json.load(open(D18_PATH, encoding="utf-8"))
        d17 = json.load(open(D17_PATH, encoding="utf-8"))
        self.assertEqual(evidence["d18_interpretation_hash"],
                         d18["content_hash"])
        self.assertEqual(evidence["d17_observation_hash"],
                         d17["normalized_hash"])
        self.assertEqual(evidence["d18_interpretation_hash"],
                         D19.verify_inputs()["d18_hash"])
        self.assertEqual(evidence["isr_hash"], D19.EXPECTED_ISR)
        self.assertEqual(evidence["d12_decision"], "NO_CHANGE")


if __name__ == "__main__":
    unittest.main()
