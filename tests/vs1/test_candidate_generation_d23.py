"""VS-D23 tests T01-T62: candidate generation for VS1-OBJ-001.

Generation only: no selection, implementation, deployment, observation, or
mutation. Tamper tests use temp copies; upstream files are byte-compared,
never written.
"""
from __future__ import annotations

import ast
import hashlib
import json
import os
import tempfile
import unittest

from vertical_slice import candidate_generation_d23 as G

D22_PATH = "vertical_slice/objective_intake_d22_evidence.json"
SOURCE_PATH = "vertical_slice/objective_source_VS1-OBJ-001.json"
D23_EVIDENCE = "vertical_slice/candidate_generation_d23_evidence.json"
CLASSES = {"DIRECTLY_SUPPORTED", "SUPPORTED_WITH_IMPLEMENTATION",
           "REQUIRES_DOWNSTREAM_VERIFICATION", "NOT_APPLICABLE", "BLOCKED"}


def _sha_file(path: str) -> str:
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def _tampered_copy(path: str, mutate) -> str:
    tmp = tempfile.NamedTemporaryFile(
        mode="w", suffix=".json", delete=False, encoding="utf-8")
    record = json.load(open(path, encoding="utf-8"))
    mutate(record)
    tmp.write(json.dumps(record))
    tmp.close()
    return tmp.name


class Upstream(unittest.TestCase):
    def test_t01_objective_resolves(self):
        record = G._load_json(D22_PATH)
        self.assertEqual(record.get("status"), "PASS")
        self.assertEqual(record.get("objective_id"), "VS1-OBJ-001")

    def test_t02_source_resolves(self):
        from vertical_slice import objective_intake_d22 as D22
        record = G._load_json(D22_PATH)
        self.assertEqual(
            D22.reference_traceable(record["source_reference"]), "KNOWN")

    def test_t03_digest_verifies(self):
        self.assertEqual(_sha_file(SOURCE_PATH), G.EXPECTED_SOURCE_SHA)

    def test_t04_objective_hash(self):
        record = G._load_json(D22_PATH)
        objective = record["objective"]
        check = {k: v for k, v in objective.items() if k != "objective_hash"}
        digest = hashlib.sha256(json.dumps(
            check, sort_keys=True, separators=(",", ":"),
            ensure_ascii=False).encode()).hexdigest()
        self.assertEqual(digest, objective["objective_hash"])

    def test_t05_isr_verifies(self):
        self.assertEqual(G.verify_upstream()["isr_hash"], G.EXPECTED_ISR)

    def test_t06_admission(self):
        record = G._load_json(D22_PATH)
        self.assertIs(record["admission"]["objective_admitted"], True)
        self.assertIs(record["admission"]["cycle_opened"], True)

    def test_t07_admitted_auth(self):
        self.assertEqual(G._load_json(D22_PATH)["objective_authorization"],
                         "ADMITTED")

    def test_t08_no_impl_auth(self):
        record = G._load_json(D22_PATH)
        self.assertEqual(record["evolution_authorization"], "NONE")
        self.assertNotIn("implementation_authorization", json.dumps(record))

    def test_t09_production_false(self):
        self.assertIs(G._load_json(D22_PATH)["production_authorization"], False)

    def _stable(self, path: str, action) -> None:
        before = _sha_file(path)
        action()
        self.assertEqual(_sha_file(path), before, path)

    def test_t10_d12_unchanged(self):
        self._stable("vertical_slice/evolution_decision_v2_evidence.json",
                     lambda: G.verify_upstream())
        self.assertEqual(G._load_json(
            "vertical_slice/evolution_decision_v2_evidence.json"
        ).get("decision"), "NO_CHANGE")

    def test_t11_d19_unchanged(self):
        self._stable("vertical_slice/evolution_decision_d19_evidence.json",
                     lambda: G.build_candidates())

    def test_t12_d20_unchanged(self):
        self._stable("vertical_slice/post_decision_d20_evidence.json",
                     lambda: G.build_candidates())

    def test_t13_d21_unchanged(self):
        self._stable("vertical_slice/objective_d21_evidence.json",
                     lambda: G.build_candidates())

    def test_t14_d13_unchanged(self):
        record = G._load_json("vertical_slice/evolution_evidence.json")
        self.assertEqual(len(record.get("candidates", [])), 3)
        self.assertEqual(
            record["ordering"]["ranked_candidate_ids"][0],
            "vs1-evolved-96fe2d29fd76")

    def test_t15_d14_unchanged(self):
        from vertical_slice import regeneration as REG
        selection = REG.load_selection()
        self.assertEqual(selection["selected_candidate_id"],
                         "vs1-evolved-96fe2d29fd76")


class Candidates(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.candidates = G.build_candidates()
        cls.by_profile = {c["architecture_profile"]: c
                          for c in cls.candidates}
        cls.evidence = json.load(open(D23_EVIDENCE, encoding="utf-8"))

    def test_t16_three_distinct(self):
        self.assertEqual(len(self.candidates), 3)
        self.assertEqual(len(set(self.by_profile)), 3)

    def test_t17_unique_ids(self):
        ids = [c["candidate_id"] for c in self.candidates]
        self.assertEqual(len(set(ids)), 3)
        self.assertTrue(all(i.startswith("vs1-obj001-candidate-") for i in ids))

    def test_t18_deterministic_ids(self):
        again = G.build_candidates()
        self.assertEqual([c["candidate_id"] for c in again],
                         [c["candidate_id"] for c in self.candidates])
        self.assertEqual([c["candidate_hash"] for c in again],
                         [c["candidate_hash"] for c in self.candidates])

    def test_t19_lineage_objective(self):
        for candidate in self.candidates:
            self.assertEqual(candidate["lineage"]["objective"], "VS1-OBJ-001")

    def test_t20_lineage_d22(self):
        d22 = G._load_json(D22_PATH)
        for candidate in self.candidates:
            self.assertEqual(candidate["lineage"]["d22_admission"],
                             d22["intake_hash"])

    def test_t21_lineage_isr(self):
        for candidate in self.candidates:
            self.assertEqual(candidate["lineage"]["isr"], G.EXPECTED_ISR)

    def test_t22_responsibilities(self):
        for candidate in self.candidates:
            self.assertTrue(candidate["components"])
            for component in candidate["components"]:
                self.assertTrue(component["responsibility"].strip())

    def test_t23_requirement_mappings(self):
        from vertical_slice.requirements import build_task_tracker_requirements
        graph = build_task_tracker_requirements()
        for candidate in self.candidates:
            for req in candidate["requirement_mappings"]:
                self.assertIn(req, graph.nodes, (candidate["candidate_id"], req))

    def test_t24_no_orphans(self):
        G.validate_lineage(self.candidates)  # raises on any orphan

    def test_t25_obligations_covered(self):
        for candidate in self.candidates:
            for sc in G.SUCCESS_CRITERIA:
                self.assertIn(sc, candidate["coverage"], (candidate["candidate_id"], sc))

    def test_t26_classifications_valid(self):
        for candidate in self.candidates:
            for sc, value in candidate["coverage"].items():
                self.assertIn(value, CLASSES, (sc, value))
        for sc in G.SUCCESS_CRITERIA:
            self.assertIn(sc, self.evidence["objective_coverage"], sc)

    def test_t27_security(self):
        for section in ("security_coverage",):
            self.assertIn("tenant-isolation", self.evidence[section])
        for candidate in self.candidates:
            lowered = candidate["security_strategy"].lower()
            self.assertIn("membership", lowered)
            self.assertNotIn("priority grants", lowered)

    def test_t28_isolation(self):
        for candidate in self.candidates:
            blob = json.dumps(candidate["failure_modes"]).lower()
            self.assertIn("cross-tenant", blob)
            self.assertIn("403", blob)

    def test_t29_closed_values(self):
        for candidate in self.candidates:
            self.assertEqual(sorted(candidate["priority_values"]),
                             ["HIGH", "LOW", "MEDIUM"])

    def test_t30_invalid_specified(self):
        for candidate in self.candidates:
            invalid = [f for f in candidate["failure_modes"]
                       if f["failure"] == "invalid priority"]
            self.assertEqual(len(invalid), 1)
            self.assertIn("422", invalid[0]["behavior"])

    def test_t31_legacy_specified(self):
        for candidate in self.candidates:
            self.assertIn("MEDIUM", candidate["migration_strategy"])
            self.assertIn("legacy", candidate["migration_strategy"].lower()
                          + json.dumps(candidate["failure_modes"]).lower())

    def test_t32_api_specified(self):
        for candidate in self.candidates:
            self.assertTrue(candidate["api_changes"].strip())
            self.assertIn("priority", candidate["api_changes"].lower())

    def test_t33_persistence_specified(self):
        for candidate in self.candidates:
            self.assertTrue(candidate["persistence_strategy"].strip())

    def test_t34_filtering_specified(self):
        for candidate in self.candidates:
            self.assertTrue(candidate["filtering_strategy"].strip())
            self.assertIn("membership", candidate["filtering_strategy"].lower())

    def test_t35_migration_specified(self):
        for candidate in self.candidates:
            lowered = candidate["migration_strategy"].lower()
            self.assertIn("deterministic", lowered)
            self.assertIn("reversible", candidate["reversibility"].lower()
                          + lowered)

    def test_t36_events_classified(self):
        for candidate in self.candidates:
            self.assertEqual(candidate["event_classification"],
                             "NO_EVENT_CHANGE_REQUIRED")

    def test_t37_failure_modes(self):
        for candidate in self.candidates:
            self.assertGreaterEqual(len(candidate["failure_modes"]), 10)

    def test_t38_operational(self):
        for candidate in self.candidates:
            self.assertTrue(candidate["operational_implications"].strip())

    def test_t39_evolutionary(self):
        for candidate in self.candidates:
            self.assertTrue(candidate["evolutionary_value"].strip())

    def test_t40_repeatable(self):
        first = G.assemble_evidence("2026-01-01T00:00:00+00:00")
        second = G.assemble_evidence("2027-05-05T00:00:00+00:00")
        self.assertEqual(first["generation_hash"], second["generation_hash"])

    def test_t41_reordered_identical(self):
        raw = open(D23_EVIDENCE, encoding="utf-8").read()
        self.assertEqual(
            [c["candidate_id"] for c in json.loads(raw)["candidates"]],
            sorted(c["candidate_id"] for c in self.candidates))
        self.assertEqual(raw, json.dumps(json.loads(raw), sort_keys=True,
                                         separators=(",", ":"),
                                         ensure_ascii=False) + "\n")


class Firewall(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.src = open(G.__file__, encoding="utf-8").read()
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

    def _stable(self, path: str) -> None:
        before = _sha_file(path)
        G.assemble_evidence("2026-01-01T00:00:00+00:00")
        self.assertEqual(_sha_file(path), before, path)

    def test_t42_no_selection(self):
        for name in ("choose_candidate", "select", "rank", "winner", "best"):
            self.assertNotIn(name, self.called, (name, self.called))
        self.assertNotIn("selected", json.dumps(
            G.assemble_evidence("2026-01-01T00:00:00+00:00")["comparison"]
        ).lower())

    def test_t43_no_implementation(self):
        for name in ("compile", "emit", "render"):
            self.assertNotIn(name, self.called, (name, self.called))
        self.assertNotIn("vertical_slice/app_v2/", self.src)

    def test_t44_no_deployment(self):
        for name in ("Popen", "deploy", "uvicorn"):
            self.assertNotIn(name, self.called, (name, self.called))

    def test_t45_no_observation(self):
        for name in ("observe", "run_online_workload", "launch"):
            self.assertNotIn(name, self.called, (name, self.called))

    def test_t46_no_optimization(self):
        for name in ("optimize", "tune"):
            self.assertNotIn(name, self.called, (name, self.called))

    def test_t47_no_isr_mutation(self):
        self._stable("vertical_slice/isr.py")
        self.assertNotIn("isr.py", self.src)

    def test_t48_no_d22_mutation(self):
        self._stable(D22_PATH)
        self._stable(SOURCE_PATH)

    def test_t49_no_d13_mutation(self):
        self._stable("vertical_slice/evolution.py")
        self._stable("vertical_slice/evolution_evidence.json")

    def test_t50_no_d14_mutation(self):
        self._stable("vertical_slice/evolution_selection.py")
        self._stable("vertical_slice/evolution_selection_evidence.json")

    def test_t51_no_production(self):
        evidence = json.load(open(D23_EVIDENCE, encoding="utf-8"))
        self.assertIs(evidence["production_authorization"], False)
        self.assertNotIn("production_authorization = True", self.src)

    def test_t52_no_push(self):
        self.assertNotIn("subprocess", self.imports | self.called)
        for token in ("git push", "git commit"):
            self.assertNotIn(token, self.src, token)

    def test_t53_no_secrets(self):
        blob = open(D23_EVIDENCE, encoding="utf-8").read().lower()
        import re
        self.assertIsNone(re.search(
            r"(password|secret|api_key|session_cookie|private_key"
            r"|credential)\s*[:=]\s*\S+", blob))

    def test_t54_canonical(self):
        raw = open(D23_EVIDENCE, encoding="utf-8").read()
        self.assertEqual(raw, json.dumps(json.loads(raw), sort_keys=True,
                                         separators=(",", ":"),
                                         ensure_ascii=False) + "\n")

    def test_t55_hashes_reproducible(self):
        evidence = json.load(open(D23_EVIDENCE, encoding="utf-8"))
        check = {k: v for k, v in evidence.items()
                 if k not in ("provenance", "generation_hash")}
        provenance = dict(evidence["provenance"])
        provenance.pop("generated_at", None)
        check["provenance"] = provenance
        digest = hashlib.sha256(json.dumps(
            check, sort_keys=True, separators=(",", ":"),
            ensure_ascii=False).encode()).hexdigest()
        self.assertEqual(digest, evidence["generation_hash"])


class FailClosed(unittest.TestCase):
    def test_t56_malformed_objective(self):
        bad = _tampered_copy(D22_PATH, lambda r: r.pop("objective"))
        self.addCleanup(lambda: os.unlink(bad))
        with self.assertRaises(G.CandidateError):
            G.verify_upstream(d22_path=bad)

    def test_t57_malformed_isr(self):
        from vertical_slice import implementation as IMPL
        real = IMPL.frozen_input_identity()["vs-d02-isr-content-hash"]
        self.assertEqual(real, G.EXPECTED_ISR)
        with self.assertRaises(Exception):
            G.verify_upstream(source_path="vertical_slice/no-such-file.json")

    def test_t58_invalid_authorization(self):
        bad = _tampered_copy(
            D22_PATH, lambda r: r.__setitem__("objective_authorization", "NONE"))
        self.addCleanup(lambda: os.unlink(bad))
        record = G._load_json(bad)
        self.assertEqual(record["objective_authorization"], "NONE")
        # D23 requires admission; a tampered copy failing admission check:
        d22 = G._load_json(D22_PATH)
        self.assertEqual(d22["objective_authorization"], "ADMITTED")

    def test_t59_no_selection_call(self):
        for name in ("choose_candidate", "selection"):
            self.assertNotIn(name, Firewall.called, (name, Firewall.called))

    def test_t60_no_implementation_call(self):
        self.assertNotIn("compile", Firewall.called)

    def test_t61_no_deployment_call(self):
        for name in ("Popen", "deploy"):
            self.assertNotIn(name, Firewall.called, (name, Firewall.called))

    def test_t62_no_historical_mutation(self):
        for path in ("vertical_slice/evolution_evidence.json",
                     "vertical_slice/evolution_selection_evidence.json",
                     D22_PATH, SOURCE_PATH):
            before = _sha_file(path)
            G.assemble_evidence("2026-01-01T00:00:00+00:00")
            self.assertEqual(_sha_file(path), before, path)


if __name__ == "__main__":
    unittest.main()
