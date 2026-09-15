"""VS-D22 tests T01-T40: objective intake (HOLD empty, PASS honest, BLOCK
closed; synthetics prove mechanics only and never open authority).
"""
from __future__ import annotations

import ast
import hashlib
import json
import unittest

from vertical_slice import objective_intake_d22 as D22

D20_PATH = "vertical_slice/post_decision_d20_evidence.json"
D19_PATH = "vertical_slice/evolution_decision_d19_evidence.json"
D12_PATH = "vertical_slice/evolution_decision_v2_evidence.json"
D22_EVIDENCE = "vertical_slice/objective_intake_d22_evidence.json"

SYN_SRC = "SYNTHETIC-TEST-ONLY:fixture-source"
SYN_AUTH = {"granted_by": "SYNTHETIC-TEST-ONLY:fixture-grantor",
            "reference": "SYNTHETIC-TEST-ONLY:fixture-auth",
            "scope": ["test.op-a"]}


def _synthetic(source_type: str, **overrides) -> dict:
    base = {
        "objective_id": "vs1-test-intake-synthetic",
        "objective_type": "synthetic-test",
        "objective_statement": "Synthetic fixture for validator exercise.",
        "source_type": source_type,
        "source_reference": SYN_SRC,
        "affected_obligations": ["req-test-only"],
        "scope": {"in_scope": ["test.op-a"], "out_of_scope": ["test.op-b"]},
        "constraints": ["test-only"],
        "success_criteria": [{"criterion": "Synthetic check.",
                              "measurement": "test assertion outcome."}],
        "security_constraints": ["no weakening (test)"],
        "authorization_reference": dict(SYN_AUTH),
    }
    base.update(overrides)
    return base


class Upstream(unittest.TestCase):
    def test_t01_d20_identity(self):
        record = D22._load_json(D20_PATH)
        self.assertEqual(record.get("contract"), "vs1-post-decision-d20")

    def test_t02_d19_identity(self):
        record = D22._load_json(D19_PATH)
        self.assertEqual(record.get("decision"), "NO_ACTION")

    def test_t03_d21_hold(self):
        record = D22._load_json("vertical_slice/objective_d21_evidence.json")
        self.assertEqual(record.get("status"), "HOLD")
        self.assertIs(record.get("cycle_opened"), False)

    def test_t04_d12_no_change(self):
        self.assertEqual(D22._load_json(D12_PATH).get("decision"), "NO_CHANGE")

    def test_t05_isr_verified(self):
        self.assertEqual(D22.verify_upstream()["isr_hash"], D22.EXPECTED_ISR)

    def test_t06_hold(self):
        outcome = D22.intake(None)
        self.assertEqual(outcome["status"], "HOLD")
        self.assertIs(outcome["objective_present"], False)
        self.assertIs(outcome["cycle_opened"], False)


class SourceTypes(unittest.TestCase):
    def _validates_mechanically(self, source_type: str):
        canonical = D22.validate_objective(_synthetic(source_type))
        self.assertEqual(canonical["source_type"], source_type)
        self.assertTrue(canonical["synthetic"])
        outcome = D22.intake(_synthetic(source_type))
        self.assertEqual(outcome["status"], "HOLD")
        self.assertIs(outcome["cycle_opened"], False)

    def test_t07_requirement_delta(self):
        self._validates_mechanically("REQUIREMENT_DELTA")

    def test_t08_new_requirement_set(self):
        self._validates_mechanically("NEW_REQUIREMENT_SET")

    def test_t09_evidence_trigger(self):
        self._validates_mechanically("EVIDENCE_TRIGGER")

    def test_t10_governing_decision(self):
        self._validates_mechanically("GOVERNING_DECISION")


class Rejections(unittest.TestCase):
    def test_t11_missing_id(self):
        bad = _synthetic("REQUIREMENT_DELTA")
        del bad["objective_id"]
        with self.assertRaises(D22.IntakeError):
            D22.validate_objective(bad)

    def test_t12_missing_source(self):
        bad = _synthetic("REQUIREMENT_DELTA")
        del bad["source_type"]
        with self.assertRaises(D22.IntakeError):
            D22.validate_objective(bad)

    def test_t13_invalid_source(self):
        with self.assertRaises(D22.IntakeError):
            D22.validate_objective(_synthetic("VIBES"))

    def test_t14_untraceable_source(self):
        with self.assertRaises(D22.IntakeError):
            D22.validate_objective(_synthetic(
                "REQUIREMENT_DELTA", source_reference="bogus"))

    def test_t15_missing_scope(self):
        bad = _synthetic("REQUIREMENT_DELTA")
        del bad["scope"]
        with self.assertRaises(D22.IntakeError):
            D22.validate_objective(bad)

    def test_t16_unbounded_scope(self):
        bad = _synthetic("REQUIREMENT_DELTA",
                         scope={"in_scope": ["test.op-a"]})
        with self.assertRaises(D22.IntakeError):
            D22.validate_objective(bad)

    def test_t17_missing_criteria(self):
        bad = _synthetic("REQUIREMENT_DELTA", success_criteria=[])
        with self.assertRaises(D22.IntakeError):
            D22.validate_objective(bad)

    def test_t18_malformed_criteria(self):
        bad = _synthetic("REQUIREMENT_DELTA",
                         success_criteria=[{"criterion": "Vague."}])
        with self.assertRaises(D22.IntakeError):
            D22.validate_objective(bad)

    def test_t19_missing_authorization(self):
        bad = _synthetic("REQUIREMENT_DELTA")
        del bad["authorization_reference"]
        with self.assertRaises(D22.IntakeError):
            D22.validate_objective(bad)

    def test_t20_insufficient_authorization(self):
        bad = _synthetic(
            "REQUIREMENT_DELTA",
            authorization_reference={"granted_by": "self",
                                     "reference": SYN_SRC,
                                     "scope": ["test.op-a"]})
        with self.assertRaises(D22.IntakeError):
            D22.validate_objective(bad)

    def test_t21_forbidden_source(self):
        for source in D22.FORBIDDEN_SOURCES:
            bad = _synthetic("REQUIREMENT_DELTA")
            bad["source_type"] = source
            with self.assertRaises(D22.IntakeError, msg=source):
                D22.validate_objective(bad)

    def test_t22_implementation_masquerade(self):
        bad = _synthetic(
            "REQUIREMENT_DELTA",
            objective_statement="Rewrite the task service using Redis workers.")
        with self.assertRaises(D22.IntakeError):
            D22.validate_objective(bad)

    def test_t23_isr_mutation(self):
        bad = _synthetic(
            "REQUIREMENT_DELTA",
            objective_statement="Rewrite ISR to support new semantics.",
            requires_isr_change=True)
        with self.assertRaises(D22.IntakeError):
            D22.validate_objective(bad)

    def test_t24_upstream_mutation(self):
        for path in (D19_PATH, D20_PATH, D12_PATH,
                     "vertical_slice/objective_d21_evidence.json"):
            with open(path, "rb") as f:
                before = hashlib.sha256(f.read()).hexdigest()
            D22.intake(None)
            with open(path, "rb") as f:
                self.assertEqual(hashlib.sha256(f.read()).hexdigest(), before,
                                 path)


class DeterminismAuthority(unittest.TestCase):
    def test_t25_canonicalization_deterministic(self):
        first = D22.validate_objective(_synthetic("REQUIREMENT_DELTA"))
        second = D22.validate_objective(_synthetic("REQUIREMENT_DELTA"))
        self.assertEqual(first["objective_hash"], second["objective_hash"])

    def test_t26_identity_deterministic(self):
        self.assertEqual(
            D22.validate_objective(
                _synthetic("GOVERNING_DECISION"))["objective_hash"],
            D22.validate_objective(
                _synthetic("GOVERNING_DECISION"))["objective_hash"])

    def test_t27_repeated_identical(self):
        first = D22.assemble_evidence(None, "2026-01-01T00:00:00+00:00")
        second = D22.assemble_evidence(None, "2027-05-05T00:00:00+00:00")
        self.assertEqual(first["intake_hash"], second["intake_hash"])

    def test_t28_synthetic_cannot_authorize(self):
        outcome = D22.intake(_synthetic("GOVERNING_DECISION"))
        self.assertIs(outcome["cycle_opened"], False)
        self.assertIs(outcome["objective_admitted"], False)
        evidence = D22.assemble_evidence(_synthetic("GOVERNING_DECISION"),
                                         "2026-01-01T00:00:00+00:00")
        self.assertEqual(evidence["objective_authorization"], "SYNTHETIC_ONLY")
        self.assertIs(evidence["admission"]["cycle_opened"], False)

    def test_t29_no_candidate_generation(self):
        # NOTE: subprocess is imported read-only for `git rev-parse HEAD`
        # (commit identity); T34 constrains it to non-mutating use.
        self.assertLessEqual(_imports(), {"__future__", "hashlib", "json",
                                          "re", "typing", "vertical_slice",
                                          "subprocess"})

    def test_t30_no_architecture_selection(self):
        for name in ("choose_candidate", "select", "rank", "generate",
                     "candidates", "mutate", "compile", "deploy", "observe",
                     "optimize", "Popen"):
            self.assertNotIn(name, _called(), (name, _called()))

    def test_t31_no_implementation(self):
        self.assertNotIn("vertical_slice/app_v2/", _src())

    def test_t32_no_deployment(self):
        self.assertNotIn("uvicorn", _src().lower())
        self.assertNotIn("serve_v2", _src())

    def test_t33_no_production(self):
        evidence = json.load(open(D22_EVIDENCE, encoding="utf-8"))
        self.assertIs(evidence["production_authorization"], False)
        self.assertNotIn("production_authorization = True", _src())

    def test_t34_no_push(self):
        for name in ("Popen", "run", "call"):
            self.assertNotIn(name, _called(), (name, _called()))
        for token in ("git push", "git commit", "checkout", '"push"', "'push'"):
            self.assertNotIn(token, _src(), token)

    def test_t35_hash_stable(self):
        first = D22.validate_objective(_synthetic("EVIDENCE_TRIGGER"))
        raw = json.dumps(first, sort_keys=True)
        self.assertEqual(json.loads(raw)["objective_hash"],
                         first["objective_hash"])

    def test_t36_forged_authorization(self):
        bad = _synthetic(
            "GOVERNING_DECISION",
            authorization_reference={"granted_by": "SYNTHETIC-TEST-ONLY:x",
                                     "reference": "FORGED-999",
                                     "scope": ["test.op-a"]})
        with self.assertRaises(D22.IntakeError):
            D22.validate_objective(bad)

    def test_t37_forged_source(self):
        bad = _synthetic("EVIDENCE_TRIGGER",
                         source_reference="EXT-::empty")
        with self.assertRaises(D22.IntakeError):
            D22.validate_objective(bad)

    def test_t38_conflicting_authority(self):
        bad = _synthetic(
            "REQUIREMENT_DELTA",
            authorization_reference={"granted_by": "SYNTHETIC-TEST-ONLY:x",
                                     "reference": SYN_SRC,
                                     "scope": ["unrelated.domain"]})
        with self.assertRaises(D22.IntakeError):
            D22.validate_objective(bad)

    def test_t39_scope_stable(self):
        canonical = D22.validate_objective(_synthetic("REQUIREMENT_DELTA"))
        self.assertTrue(D22.operation_in_scope(canonical, "test.op-a"))
        self.assertFalse(D22.operation_in_scope(canonical, "test.op-b"))
        self.assertFalse(D22.operation_in_scope(canonical, "test.op-new"))

    def test_t40_prior_unchanged(self):
        for path in (D19_PATH, D20_PATH,
                     "vertical_slice/objective_d21_evidence.json"):
            with open(path, "rb") as f:
                before = hashlib.sha256(f.read()).hexdigest()
            D22.intake(_synthetic("REQUIREMENT_DELTA"))
            with open(path, "rb") as f:
                self.assertEqual(hashlib.sha256(f.read()).hexdigest(), before,
                                 path)


def _imports() -> set[str]:
    tree = ast.parse(open(D22.__file__, encoding="utf-8").read())
    imports: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.update(a.name for a in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.add(node.module)
    return imports


def _called() -> set[str]:
    tree = ast.parse(open(D22.__file__, encoding="utf-8").read())
    called: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            func = node.func
            called.add(func.id if isinstance(func, ast.Name)
                       else func.attr if isinstance(func, ast.Attribute)
                       else "")
    return called


def _src() -> str:
    return open(D22.__file__, encoding="utf-8").read()


class ContentAddressedRecords(unittest.TestCase):
    REC = "vertical_slice/objective_source_VS1-OBJ-001.json"

    def _digest(self) -> str:
        with open(self.REC, "rb") as f:
            return hashlib.sha256(f.read()).hexdigest()

    def _ref(self, digest: str | None = None, path: str | None = None) -> str:
        return "REPO#%s#sha256:%s" % (path or self.REC, digest or self._digest())

    def test_t41_verified_record_resolves(self):
        self.assertEqual(D22.reference_traceable(self._ref()), "KNOWN")

    def test_t42_tampered_digest_blocked(self):
        bad = self._digest()[:-1] + ("0" if self._digest()[-1] != "0" else "1")
        self.assertEqual(D22.reference_traceable(self._ref(bad)), "UNTRACEABLE")
        with self.assertRaises(D22.IntakeError):
            D22.validate_objective(_synthetic(
                "REQUIREMENT_DELTA", source_reference=self._ref(bad)))

    def test_t43_missing_file_blocked(self):
        ref = self._ref(path="vertical_slice/no-such-record.json")
        self.assertEqual(D22.reference_traceable(ref), "UNTRACEABLE")

    def test_t44_path_escape_blocked(self):
        ref = "REPO#../outside.json#sha256:%s" % self._digest()
        self.assertEqual(D22.reference_traceable(ref), "UNTRACEABLE")

    def test_t45_admitted_objective_verifies(self):
        evidence = json.load(open(D22_EVIDENCE, encoding="utf-8"))
        self.assertEqual(evidence["status"], "PASS")
        self.assertEqual(evidence["objective_id"], "VS1-OBJ-001")
        self.assertIs(evidence["admission"]["objective_admitted"], True)
        self.assertIs(evidence["admission"]["cycle_opened"], True)
        self.assertEqual(evidence["objective_authorization"], "ADMITTED")
        check = {k: v for k, v in evidence.items()
                 if k not in ("provenance", "intake_hash")}
        provenance = dict(evidence["provenance"])
        provenance.pop("generated_at", None)
        check["provenance"] = provenance
        digest = hashlib.sha256(json.dumps(
            check, sort_keys=True, separators=(",", ":"),
            ensure_ascii=False).encode()).hexdigest()
        self.assertEqual(digest, evidence["intake_hash"])


if __name__ == "__main__":
    unittest.main()
