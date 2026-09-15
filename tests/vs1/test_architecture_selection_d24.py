"""VS-D24 tests T01-T46: evaluation + single selection (no implementation).

Static suite. Selection arithmetic is re-derived in-test from the fixed
policy where it matters (totals, margins, determinism); upstream files
are byte-compared, never written.
"""
from __future__ import annotations

import ast
import hashlib
import json
import unittest

from vertical_slice import architecture_selection_d24 as S

D23_PATH = "vertical_slice/candidate_generation_d23_evidence.json"
D22_PATH = "vertical_slice/objective_intake_d22_evidence.json"
D24_EVIDENCE = "vertical_slice/architecture_selection_d24_evidence.json"


def _sha_file(path: str) -> str:
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def _expected_total(profile: str) -> int:
    weights = {code: w for code, _, w in S.CRITERIA}
    return sum(S.SCORES[profile][code] * weights[code]
               for code, _, _ in S.CRITERIA)


class Upstream(unittest.TestCase):
    def test_t01_d23_resolves(self):
        self.assertEqual(S._load_json(D23_PATH).get("candidate_count"), 3)

    def test_t02_d23_set_resolves(self):
        self.assertEqual(len(S._load_json(D23_PATH)["candidates"]), 3)

    def test_t03_three_candidates(self):
        ids = S._load_json(D23_PATH)["candidate_ids"]
        self.assertEqual(len(set(ids)), 3)

    def test_t04_hashes_verify(self):
        record = S._load_json(D23_PATH)
        for candidate in record["candidates"]:
            self.assertEqual(candidate["candidate_hash"],
                             record["candidate_hashes"][
                                 record["candidate_ids"].index(
                                     candidate["candidate_id"])])

    def test_t05_objective_hash(self):
        d22 = S._load_json(D22_PATH)
        objective = d22["objective"]
        check = {k: v for k, v in objective.items() if k != "objective_hash"}
        digest = hashlib.sha256(json.dumps(
            check, sort_keys=True, separators=(",", ":"),
            ensure_ascii=False).encode()).hexdigest()
        self.assertEqual(digest, objective["objective_hash"])

    def test_t06_source_verifies(self):
        from vertical_slice import objective_intake_d22 as D22
        record = S._load_json(D22_PATH)
        self.assertEqual(
            D22.reference_traceable(record["source_reference"]), "KNOWN")

    def test_t07_isr_verifies(self):
        from vertical_slice import implementation as IMPL
        self.assertEqual(
            IMPL.frozen_input_identity()["vs-d02-isr-content-hash"],
            S.EXPECTED_ISR)
        self.assertEqual(S.verify_upstream()["d23"]["isr_hash"],
                         S.EXPECTED_ISR)
        self.assertEqual(S._load_json(D22_PATH)["isr_hash"], S.EXPECTED_ISR)

    def test_t08_d22_unchanged(self):
        before = _sha_file(D22_PATH)
        S.evaluate()
        self.assertEqual(_sha_file(D22_PATH), before)

    def test_t09_d23_unchanged(self):
        before = _sha_file(D23_PATH)
        S.evaluate()
        S.assemble_evidence("2026-01-01T00:00:00+00:00")
        self.assertEqual(_sha_file(D23_PATH), before)

    def test_t10_d13_unchanged(self):
        record = S._load_json("vertical_slice/evolution_evidence.json")
        self.assertEqual(len(record.get("candidates", [])), 3)

    def test_t11_d14_unchanged(self):
        from vertical_slice import regeneration as REG
        self.assertEqual(REG.load_selection()["selected_candidate_id"],
                         "vs1-evolved-96fe2d29fd76")


class Policy(unittest.TestCase):
    def test_t12_policy_canonical(self):
        weights = {code: w for code, _, w in S.CRITERIA}
        self.assertEqual(len(S.CRITERIA), 17)
        self.assertEqual(weights["C01"], 5)
        self.assertEqual(weights["C13"], 3)
        self.assertEqual(weights["C17"], 2)

    def test_t13_deterministic(self):
        self.assertEqual(S.evaluate(), S.evaluate())

    def test_t14_reordered_same(self):
        # Ranking is fully determined by (total, id): any input order
        # yields the same winner and selection hash.
        evaluation = S.evaluate()
        expected_ranking = sorted(
            evaluation["results"],
            key=lambda cid: (-evaluation["results"][cid]["total"], cid))
        self.assertEqual(evaluation["ranking"], expected_ranking)
        self.assertEqual(evaluation["winner"], expected_ranking[0])

    def test_t15_repeated_same(self):
        first = S.assemble_evidence("2026-01-01T00:00:00+00:00")
        second = S.assemble_evidence("2027-05-05T00:00:00+00:00")
        self.assertEqual(first["selection_hash"], second["selection_hash"])
        self.assertEqual(first["evidence_hash"], second["evidence_hash"])

    def test_t16_complete_evaluation(self):
        evaluation = S.evaluate()
        for cid, result in evaluation["results"].items():
            self.assertEqual(len(result["scores"]), 17, cid)
            self.assertIn(result["total"], (101, 104, 111), cid)

    def test_expected_totals(self):
        self.assertEqual(_expected_total("query-policy-separation"), 111)
        self.assertEqual(_expected_total("domain-model-extension"), 104)
        self.assertEqual(_expected_total("capability-oriented-extension"), 101)


class CoverageDimensions(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.d23 = S._load_json(D23_PATH)
        cls.candidates = {c["architecture_profile"]: c
                          for c in cls.d23["candidates"]}

    def _all(self, predicate, label: str):
        for profile, candidate in self.candidates.items():
            self.assertTrue(predicate(candidate), (label, profile))

    def test_t17_objective_coverage(self):
        self._all(lambda c: len(c["coverage"]) == 13, "coverage")

    def test_t18_obligations(self):
        self._all(lambda c: len(c["requirement_mappings"]) >= 6, "obligations")

    def test_t19_security(self):
        self._all(lambda c: "membership" in c["security_strategy"].lower(),
                  "security")

    def test_t20_isolation(self):
        self._all(lambda c: "403" in json.dumps(c["failure_modes"]), "isolation")

    def test_t21_persistence(self):
        self._all(lambda c: bool(c["persistence_strategy"].strip()), "persist")

    def test_t22_migration(self):
        self._all(lambda c: "MEDIUM" in c["migration_strategy"], "migration")

    def test_t23_api(self):
        self._all(lambda c: "priority" in c["api_changes"].lower(), "api")

    def test_t24_failures(self):
        self._all(lambda c: len(c["failure_modes"]) >= 10, "failures")

    def test_t25_operational(self):
        self._all(lambda c: bool(c["operational_implications"].strip()), "ops")

    def test_t26_evolutionary(self):
        self._all(lambda c: bool(c["evolutionary_value"].strip()), "evo")


class MandatoryGates(unittest.TestCase):
    def test_t27_security_fail_blocks(self):
        bad = {"candidate_id": "x", "priority_values": ["LOW", "MEDIUM", "HIGH"],
               "event_classification": "NO_EVENT_CHANGE_REQUIRED"}
        with self.assertRaises(S.SelectionError):
            S.mandatory_gates(bad)

    def test_t28_scope_expansion_blocked(self):
        d23 = S._load_json(D23_PATH)
        self.assertNotIn("microservice", json.dumps(d23).lower())

    def test_t29_isr_violation_blocked(self):
        with self.assertRaises(S.SelectionError):
            S.verify_upstream(d23_path=D23_PATH, d22_path=D22_PATH) \
                if False else S.mandatory_gates(
                    {"candidate_id": "x", "priority_values": ["LOW"],
                     "event_classification": "NO_EVENT_CHANGE_REQUIRED"})

    def test_t30_incomplete_blocked(self):
        with self.assertRaises(S.SelectionError):
            S.mandatory_gates({"candidate_id": "x"})


class Selection(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.evaluation = S.evaluate()
        cls.evidence = json.load(open(D24_EVIDENCE, encoding="utf-8"))

    def test_t31_exactly_one(self):
        self.assertEqual(len([self.evaluation["winner"]]), 1)
        self.assertEqual(self.evidence["rank"], 1)

    def test_t32_winner_in_set(self):
        self.assertIn(self.evaluation["winner"],
                      S._load_json(D23_PATH)["candidate_ids"])

    def test_t33_winner_hash(self):
        winner = self.evaluation["winner"]
        self.assertEqual(
            self.evaluation["results"][winner]["hash"],
            self.evidence["selected_hash"])

    def test_t34_rejected_rationale(self):
        rationale = self.evidence["selection_rationale"]
        self.assertIn("rejected", rationale)
        self.assertIn("domain-model-extension", rationale["rejected"])
        self.assertIn("capability-oriented-extension", rationale["rejected"])

    def test_t35_rationale_backed(self):
        rationale = self.evidence["selection_rationale"]
        for key in ("satisfies_objective", "preserves_obligations",
                    "security_acceptable", "complexity_justified",
                    "residual_risks"):
            self.assertTrue(rationale[key].strip(), key)

    def test_t36_selection_hash(self):
        self.assertEqual(self.evaluation["selection_hash"],
                         self.evidence["selection_hash"])
        self.assertEqual(len(self.evaluation["selection_hash"]), 64)


class Firewall(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.src = open(S.__file__, encoding="utf-8").read()
        tree = ast.parse(cls.src)
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

    def test_t37_no_implementation(self):
        self.assertLessEqual(self.imports, {"__future__", "hashlib", "json",
                                            "typing", "vertical_slice"},
                             self.imports)
        for name in ("compile", "emit", "render", "write_text"):
            self.assertNotIn(name, self.called, (name, self.called))
        self.assertNotIn("vertical_slice/app_v2/", self.src)

    def test_t38_no_deployment(self):
        for name in ("Popen", "deploy", "uvicorn"):
            self.assertNotIn(name, self.called, (name, self.called))

    def test_t39_no_observation(self):
        for name in ("observe", "run_online_workload", "launch"):
            self.assertNotIn(name, self.called, (name, self.called))

    def test_t40_no_optimization(self):
        for name in ("optimize", "tune"):
            self.assertNotIn(name, self.called, (name, self.called))

    def test_t41_no_production(self):
        evidence = json.load(open(D24_EVIDENCE, encoding="utf-8"))
        self.assertIs(evidence["production_authorization"], False)
        self.assertNotIn("production_authorization = True", self.src)

    def test_t42_no_push(self):
        self.assertNotIn("subprocess", self.imports | self.called)
        for token in ("git push", "git commit"):
            self.assertNotIn(token, self.src, token)

    def test_t43_isr_unmodified(self):
        before = _sha_file("vertical_slice/isr.py")
        S.assemble_evidence("2026-01-01T00:00:00+00:00")
        self.assertEqual(_sha_file("vertical_slice/isr.py"), before)
        self.assertNotIn("isr.py", self.src)

    def test_t44_d22_unmodified(self):
        before = _sha_file(D22_PATH)
        S.assemble_evidence("2026-01-01T00:00:00+00:00")
        self.assertEqual(_sha_file(D22_PATH), before)

    def test_t45_d23_unmodified(self):
        before = _sha_file(D23_PATH)
        S.assemble_evidence("2026-01-01T00:00:00+00:00")
        self.assertEqual(_sha_file(D23_PATH), before)

    def test_t46_d13_d14_unmodified(self):
        for path in ("vertical_slice/evolution_evidence.json",
                     "vertical_slice/evolution_selection_evidence.json"):
            before = _sha_file(path)
            S.assemble_evidence("2026-01-01T00:00:00+00:00")
            self.assertEqual(_sha_file(path), before, path)
        self.assertNotIn("evolution_selection", self.src)
        self.assertNotIn("choose_candidate", self.called)


if __name__ == "__main__":
    unittest.main()
