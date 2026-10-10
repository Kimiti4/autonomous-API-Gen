from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from input_snapshot import SnapshotError, capture_snapshot, verify_snapshot


class InputSnapshotTests(unittest.TestCase):
    def make_trial(self, root: Path) -> None:
        (root / "specs").mkdir()
        (root / "PROBLEM.md").write_text("A neutral app specification.\n", encoding="utf-8")
        (root / "ACCEPTANCE.json").write_text('{"required":["create","read"]}\n', encoding="utf-8")
        contract = {
            "trial_id": "SNAPSHOT-TEST",
            "generator_inputs": ["PROBLEM.md", "ACCEPTANCE.json"],
            "forbidden_inputs": ["golden/app"],
        }
        (root / "TRIAL_CONTRACT.json").write_text(
            json.dumps(contract, sort_keys=True) + "\n", encoding="utf-8"
        )

    def test_snapshot_verifies_when_sources_are_unchanged(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.make_trial(root)
            manifest = capture_snapshot(root, root / "out" / "evidence")
            self.assertEqual(len(manifest["inputs"]), 2)
            result = verify_snapshot(root, root / "out" / "evidence")
            self.assertEqual(result["verdict"], "PASS")
            self.assertEqual(result["issues"], [])

    def test_source_change_is_detected_after_snapshot(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.make_trial(root)
            capture_snapshot(root, root / "out" / "evidence")
            (root / "PROBLEM.md").write_text("Changed after run.\n", encoding="utf-8")
            result = verify_snapshot(root, root / "out" / "evidence")
            self.assertEqual(result["verdict"], "FAIL")
            self.assertIn("source_input_changed:PROBLEM.md", result["issues"])

    def test_contract_change_is_detected_after_snapshot(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.make_trial(root)
            capture_snapshot(root, root / "out" / "evidence")
            (root / "TRIAL_CONTRACT.json").write_text('{"changed":true}\n', encoding="utf-8")
            result = verify_snapshot(root, root / "out" / "evidence")
            self.assertEqual(result["verdict"], "FAIL")
            self.assertIn("source_contract_changed", result["issues"])

    def test_path_traversal_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.make_trial(root)
            contract_path = root / "TRIAL_CONTRACT.json"
            contract = json.loads(contract_path.read_text(encoding="utf-8"))
            contract["generator_inputs"] = ["../outside.txt"]
            contract_path.write_text(json.dumps(contract), encoding="utf-8")
            with self.assertRaises(SnapshotError):
                capture_snapshot(root, root / "out" / "evidence")

    def test_forbidden_input_cannot_be_declared(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.make_trial(root)
            forbidden = root / "golden" / "app"
            forbidden.mkdir(parents=True)
            (forbidden / "main.py").write_text("must not be copied", encoding="utf-8")
            contract_path = root / "TRIAL_CONTRACT.json"
            contract = json.loads(contract_path.read_text(encoding="utf-8"))
            contract["generator_inputs"] = ["golden/app/main.py"]
            contract_path.write_text(json.dumps(contract), encoding="utf-8")
            with self.assertRaises(SnapshotError):
                capture_snapshot(root, root / "out" / "evidence")


if __name__ == "__main__":
    unittest.main()
