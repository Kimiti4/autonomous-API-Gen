"""VS-D28 tests T01-T28: epistemic compiler (no runtime, no mutation).

Includes the four end-to-end demonstrations required by the gate:
raw→hash, tamper→rejection, unsupported→rejection, conflict→CONTRADICTION.
"""
from __future__ import annotations

import argparse
import ast
import copy
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

import sys

sys.path.insert(0, str(ROOT))

from vertical_slice import runtime_interpretation_d28 as D28  # noqa: E402

FIX = Path(__file__).resolve().parent / "fixtures" / "d28"
REAL_EVIDENCE = ROOT / "vertical_slice/runtime_observation_d27_evidence.json"
POLICY_PATH = ROOT / "vertical_slice/runtime_interpretation_policy_d28.json"
REAL_HASH = "731ee7a264906f446a09b8f9fd6c4a181c8b08456c3348e8092180345cedf774"


def _fixture(name: str) -> dict:
    return json.loads((FIX / name).read_text(encoding="utf-8"))


def _run_fixture(name: str, tmp: Path):
    # Fixture runs bind their own content hash (read from the fixture),
    # preserving the integrity-binding property without demanding the
    # production evidence prefix.
    fixture_hash = json.loads((FIX / name).read_text(
        encoding="utf-8"))["normalized_hash"]
    out = tmp / "out"
    docs = tmp / "docs"
    args = argparse.Namespace(
        d27_evidence=str(FIX / name),
        policy=str(POLICY_PATH), expected_d27_hash=fixture_hash,
        write=True, out_dir=str(out), docs_dir=str(docs))
    return D28.run_d28(args), out, docs


def _receivers() -> set:
    tree = ast.parse(Path(D28.__file__).read_text(encoding="utf-8"))
    pairs: set = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            func = node.func
            if isinstance(func, ast.Attribute):
                receiver = func.value.id if isinstance(
                    func.value, ast.Name) else ""
                pairs.add((func.attr, receiver))
    return pairs


def _interpret(name: str):
    """Full interpret pipeline on a fixture, in-memory where possible."""
    evidence = _fixture(name)
    D28.verify_provenance(evidence)
    policy = D28.load_json(POLICY_PATH, "D28 policy")
    observations = D28.normalize_observations(evidence)
    contradictions = D28.detect_contradictions(observations)
    coverage, criterion_claims, unknowns = D28.evaluate_criteria(
        policy, observations, contradictions)
    inference_claims = D28.evaluate_inferences(policy, observations)
    return {"evidence": evidence, "policy": policy,
            "observations": observations, "contradictions": contradictions,
            "coverage": coverage,
            "claims": criterion_claims + inference_claims,
            "unknowns": unknowns}


class Ingestion(unittest.TestCase):
    def test_t01_valid_evidence(self):
        evidence = D28.verify_evidence_file(REAL_EVIDENCE, REAL_HASH)
        self.assertEqual(evidence["execution_id"], "vs1-d27-run-001")

    def test_t02_policy_verifies(self):
        policy = D28.load_json(POLICY_PATH, "D28 policy")
        self.assertEqual(policy["policy_version"], "d28-policy-v1")
        self.assertEqual(len(policy["criteria"]), 13)
        self.assertTrue(policy["inferences"])
        self.assertIn("production", policy["forbidden_scopes"])


class Determinism(unittest.TestCase):
    def test_t03_normalize_deterministic(self):
        evidence = _fixture("d27_evidence_valid.json")
        first = D28.normalize_observations(evidence)
        second = D28.normalize_observations(_fixture("d27_evidence_valid.json"))
        self.assertEqual(D28.canonical_json(first), D28.canonical_json(second))

    def test_t04_reorder_stable(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            code_a, _, _ = _run_fixture("d27_evidence_valid.json", tmp_path)
            code_b, _, _ = _run_fixture("d27_evidence_reordered.json", tmp_path)
            self.assertEqual(code_a, 0)
            self.assertEqual(code_b, 0)
            hash_a = json.loads((tmp_path / "out"
                                 / "runtime_interpretation_d28_evidence.json")
                                .read_text())["interpretation_hash"]
            # Reordered run overwrote same out dir; rerun separately below.
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            _run_fixture("d27_evidence_reordered.json", tmp_path)
            hash_b = json.loads((tmp_path / "out"
                                 / "runtime_interpretation_d28_evidence.json")
                                .read_text())["interpretation_hash"]
        self.assertEqual(hash_a, hash_b)

    def test_t05_timestamp_invariant(self):
        evidence = _fixture("d27_evidence_valid.json")
        mutated = copy.deepcopy(evidence)
        mutated["observations"][0]["timestamp"] = "1999-12-31T23:59:59Z"
        self.assertEqual(
            D28.canonical_json(D28.normalize_observations(evidence)),
            D28.canonical_json(D28.normalize_observations(mutated)))

    def test_t06_latency_invariant(self):
        evidence = _fixture("d27_evidence_valid.json")
        mutated = copy.deepcopy(evidence)
        mutated["observations"][0]["measurement"] = {"http_status": 200,
                                                     "latency_ms": 9999.0}
        self.assertEqual(
            D28.canonical_json(D28.normalize_observations(evidence)),
            D28.canonical_json(D28.normalize_observations(mutated)))

    def test_t07_semantic_change_detected(self):
        evidence = _fixture("d27_evidence_valid.json")
        mutated = copy.deepcopy(evidence)
        record = mutated["observations"][0]
        record["observed_class"] = "http-500"
        record["status"] = "FAIL"
        mutated["summary"]["status_counts"] = {
            "PASS": 2, "FAIL": 1, "UNDETERMINED": 0, "BLOCKED": 0}
        self.assertNotEqual(
            D28.canonical_json(D28.normalize_observations(evidence)),
            D28.canonical_json(D28.normalize_observations(mutated)))


class Forgery(unittest.TestCase):
    def test_t08_forged_success(self):
        with self.assertRaises(D28.FailClosed):
            D28.normalize_observations(_fixture("d27_evidence_forged_success.json"))

    def test_t09_forged_priority(self):
        with self.assertRaises(D28.FailClosed):
            D28.normalize_observations(_fixture("d27_evidence_forged_priority.json"))

    def test_t10_forged_auth(self):
        with self.assertRaises(D28.FailClosed):
            D28.normalize_observations(_fixture("d27_evidence_forged_auth.json"))

    def test_t11_forged_persistence(self):
        with self.assertRaises(D28.FailClosed):
            D28.normalize_observations(
                _fixture("d27_evidence_forged_persistence.json"))

    def test_t12_forged_provenance(self):
        with self.assertRaises(D28.FailClosed):
            D28.verify_provenance(_fixture("d27_evidence_forged_provenance.json"))

    def test_t13_forged_hash(self):
        with self.assertRaises(D28.FailClosed):
            D28.verify_evidence_file(REAL_EVIDENCE, "0" * 64)

    def test_t14_missing_observation(self):
        result = _interpret("d27_evidence_missing_observation.json")
        sc02 = next(c for c in result["coverage"] if c["criterion_id"] == "SC02")
        self.assertEqual(sc02["status"], "UNKNOWN")

    def test_t15_missing_provenance(self):
        evidence = _fixture("d27_evidence_valid.json")
        del evidence["execution_id"]
        with self.assertRaises(D28.FailClosed):
            D28.verify_provenance(evidence)


class Epistemics(unittest.TestCase):
    def test_t16_contradiction_emitted(self):
        atoms = [
            {"observation_id": "a", "semantic_key": "k", "result": "success",
             "tags": []},
            {"observation_id": "b", "semantic_key": "k", "result": "failure",
             "tags": []},
        ]
        contradictions = D28.detect_contradictions(atoms)
        self.assertEqual(len(contradictions), 1)
        self.assertEqual(contradictions[0]["resolution_status"], "UNRESOLVED")

    def test_t17_contradiction_blocks_promotion(self):
        policy = {"criteria": [{"id": "SCX", "text": "X",
                                "required_tag_sets": [["t"]]}]}
        atoms = [
            {"observation_id": "a", "semantic_key": "k", "result": "success",
             "tags": ["t"]},
            {"observation_id": "b", "semantic_key": "k", "result": "failure",
             "tags": ["t"]},
        ]
        contradictions = D28.detect_contradictions(atoms)
        coverage, claims, _ = D28.evaluate_criteria(policy, atoms, contradictions)
        self.assertEqual(coverage[0]["status"], "CONTRADICTION")
        self.assertFalse([c for c in claims
                          if c["epistemic_class"] == "OBSERVED"])

    def test_t18_unsupported_inference(self):
        policy = {"inferences": [{"claim_id": "INF-X",
                                  "statement": "Baseless.",
                                  "required_tag_sets": [["nope"]],
                                  "reasoning": "None."}]}
        self.assertEqual(D28.evaluate_inferences(policy, []), [])

    def test_t19_inference_without_observations(self):
        policy = D28.load_json(POLICY_PATH, "D28 policy")
        self.assertEqual(D28.evaluate_inferences(policy, []), [])

    def test_t20_overgeneralization_rejected(self):
        rejected = D28.evaluate_overgeneralizations()
        self.assertEqual(len(rejected), 5)
        self.assertTrue(all(r["actual_classification"] == "REJECTED AS UNSUPPORTED"
                            for r in rejected))

    def test_t21_scope_expansion_rejected(self):
        policy = D28.load_json(POLICY_PATH, "D28 policy")
        with self.assertRaises(D28.FailClosed):
            D28.validate_claim_scope(
                {"claim_id": "X", "scope": ["production"]}, policy)

    def test_t22_secret_shaped_evidence(self):
        self.assertIn("generic_password",
                      D28.scan_for_secrets(
                          {"note": "password = \"abcdefgh\""}))
        self.assertIn("json_secret_key",
                      D28.scan_for_secrets({"password": "abcdefgh"}))
        self.assertEqual(D28.scan_for_secrets({"status": "ok"}), [])


class Boundaries(unittest.TestCase):
    def test_t23_no_runtime(self):
        tree = ast.parse(Path(D28.__file__).read_text(encoding="utf-8"))
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
        self.assertLessEqual(imports, {"__future__", "argparse", "hashlib",
                                       "json", "re", "sys", "pathlib",
                                       "typing"}, imports)
        # NOTE: re.compile is regex construction, not implementation
        # compilation; it is excluded by receiver below.
        receivers = _receivers()
        for name in ("urlopen", "request", "Popen", "run", "socket",
                     "check_output", "deploy", "optimize",
                     "decide", "select", "generate", "push"):
            self.assertNotIn(name, called, (name, called))
        self.assertNotIn("compile", {c for c, r in receivers if r != "re"},
                         receivers)

    def test_t24_no_deployment(self):
        src = Path(D28.__file__).read_text(encoding="utf-8").lower()
        self.assertNotIn("serve_v3", src)
        self.assertNotIn("uvicorn", src)

    def test_t25_no_implementation_mutation(self):
        before = {str(p): p.stat().st_mtime_ns for p in
                  (ROOT / "vertical_slice/app_v3").rglob("*.py")}
        D28.normalize_observations(_fixture("d27_evidence_valid.json"))
        after = {str(p): p.stat().st_mtime_ns for p in
                 (ROOT / "vertical_slice/app_v3").rglob("*.py")}
        self.assertEqual(before, after)

    def test_t26_upstream_stable(self):
        paths = [ROOT / "vertical_slice/runtime_observation_d27_evidence.json",
                 ROOT / "vertical_slice/deployment_d26_evidence.json",
                 ROOT / "vertical_slice/isr.py"]
        before = {str(p): p.stat().st_size for p in paths}
        D28.normalize_observations(_fixture("d27_evidence_valid.json"))
        after = {str(p): p.stat().st_size for p in paths}
        self.assertEqual(before, after)

    def test_t27_canonical_repeat(self):
        import tempfile
        with tempfile.TemporaryDirectory() as first, \
                tempfile.TemporaryDirectory() as second:
            _run_fixture("d27_evidence_valid.json", Path(first))
            _run_fixture("d27_evidence_valid.json", Path(second))
            hash_first = json.loads((Path(first) / "out"
                                     / "runtime_interpretation_d28_evidence.json")
                                    .read_text())["interpretation_hash"]
            hash_second = json.loads((Path(second) / "out"
                                      / "runtime_interpretation_d28_evidence.json")
                                     .read_text())["interpretation_hash"]
            self.assertEqual(hash_first, hash_second)

    def test_t28_handoff_closed(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            _run_fixture("d27_evidence_valid.json", Path(tmp))
            handoff = json.loads((Path(tmp) / "out"
                                  / "runtime_interpretation_d28_handoff.json")
                                 .read_text())
            self.assertEqual(handoff["next_gate"], "D29")
            self.assertEqual(handoff["authorization_state"],
                             "D29_AUTHORIZATION=NOT GRANTED")


if __name__ == "__main__":
    unittest.main()
