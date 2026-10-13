"""Tests for fail-closed TaskFlow decision-ledger consistency validation."""
from __future__ import annotations

import importlib.util
import json
import shutil
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
VALIDATOR_PATH = REPO_ROOT / "experiments/taskflow-native/validate_decision_ledger.py"
SPEC = importlib.util.spec_from_file_location("taskflow_decision_ledger_validator", VALIDATOR_PATH)
assert SPEC is not None and SPEC.loader is not None
validator = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(validator)


class DecisionLedgerValidationTests(unittest.TestCase):
    def test_git_blob_sha_uses_git_object_header(self) -> None:
        self.assertEqual(
            validator.git_blob_sha(b"test\n"),
            "9daeafb9864cf43055ae93beb0afd6c7d144bfa4",
        )

    def test_current_review_artifacts_are_consistent(self) -> None:
        errors = validator.validate(REPO_ROOT)
        self.assertEqual(errors, [], "\n".join(errors))

    def test_open_decisions_cannot_silently_claim_approval(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            required = [
                validator.LEDGER_PATH,
                validator.MATRIX_PATH,
                validator.PROBLEM_PATH,
                validator.ACCEPTANCE_PATH,
                validator.OPEN_DECISIONS_PATH,
                validator.CONSUMER_TRACE_PATH,
            ]
            ledger = json.loads((REPO_ROOT / validator.LEDGER_PATH).read_text(encoding="utf-8"))
            required.extend(Path(record["source_record"]) for record in ledger["records"])
            for relative in required:
                target = root / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(REPO_ROOT / relative, target)

            docket_path = root / validator.OPEN_DECISIONS_PATH
            docket = json.loads(docket_path.read_text(encoding="utf-8"))
            docket["decisions"][0]["reviewer_answer"] = "assumed default"
            docket_path.write_text(json.dumps(docket), encoding="utf-8")

            errors = validator.validate(root)
            self.assertTrue(
                any("open decision must not contain an answer" in error for error in errors),
                errors,
            )

    def test_unverified_consumer_cannot_claim_pass(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            required = [
                validator.LEDGER_PATH,
                validator.MATRIX_PATH,
                validator.PROBLEM_PATH,
                validator.ACCEPTANCE_PATH,
                validator.OPEN_DECISIONS_PATH,
                validator.CONSUMER_TRACE_PATH,
            ]
            ledger = json.loads((REPO_ROOT / validator.LEDGER_PATH).read_text(encoding="utf-8"))
            required.extend(Path(record["source_record"]) for record in ledger["records"])
            for relative in required:
                target = root / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(REPO_ROOT / relative, target)

            trace_path = root / validator.CONSUMER_TRACE_PATH
            trace = json.loads(trace_path.read_text(encoding="utf-8"))
            trace["fields"][0]["status"] = "PASS"
            trace_path.write_text(json.dumps(trace), encoding="utf-8")

            errors = validator.validate(root)
            self.assertTrue(
                any("consumer status must remain BLOCKED" in error for error in errors),
                errors,
            )

    def test_duplicate_semantic_mapping_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            required = [
                validator.LEDGER_PATH,
                validator.MATRIX_PATH,
                validator.PROBLEM_PATH,
                validator.ACCEPTANCE_PATH,
                validator.OPEN_DECISIONS_PATH,
                validator.CONSUMER_TRACE_PATH,
            ]
            ledger = json.loads((REPO_ROOT / validator.LEDGER_PATH).read_text(encoding="utf-8"))
            required.extend(Path(record["source_record"]) for record in ledger["records"])
            for relative in required:
                target = root / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(REPO_ROOT / relative, target)

            matrix_path = root / validator.MATRIX_PATH
            matrix = json.loads(matrix_path.read_text(encoding="utf-8"))
            matrix["semantic_groups"][1]["id"] = matrix["semantic_groups"][0]["id"]
            matrix_path.write_text(json.dumps(matrix), encoding="utf-8")

            errors = validator.validate(root)
            self.assertTrue(
                any("matrix semantic_groups must contain 15 unique IDs" in error for error in errors),
                errors,
            )


if __name__ == "__main__":
    unittest.main()
