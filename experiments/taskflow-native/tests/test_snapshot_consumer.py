from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

TRIAL_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TRIAL_DIR))

from input_snapshot import capture_snapshot  # noqa: E402
from snapshot_consumer import SnapshotConsumptionError, load_snapshot_inputs  # noqa: E402


class SnapshotConsumerTests(unittest.TestCase):
    def make_trial(self, root: Path) -> None:
        (root / "PROBLEM.md").write_text("Canonical neutral spec\n", encoding="utf-8")
        (root / "ACCEPTANCE.json").write_text('{"required":["auth","projects"]}\n', encoding="utf-8")
        (root / "TRIAL_CONTRACT.json").write_text(
            json.dumps({
                "trial_id": "CONSUMER-TEST",
                "generator_inputs": ["PROBLEM.md", "ACCEPTANCE.json"],
                "forbidden_inputs": ["golden/app"],
            }) + "\n",
            encoding="utf-8",
        )

    def test_returns_only_verified_snapshot_paths(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.make_trial(root)
            evidence = root / "out" / "evidence"
            capture_snapshot(root, evidence)
            result = load_snapshot_inputs(evidence)
            self.assertEqual(set(result["inputs"]), {"PROBLEM.md", "ACCEPTANCE.json"})
            self.assertTrue(all(path.is_relative_to(evidence) for path in result["inputs"].values()))
            self.assertEqual(result["inputs"]["PROBLEM.md"].read_text(encoding="utf-8"), "Canonical neutral spec\n")

    def test_source_mutation_does_not_change_generation_snapshot(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.make_trial(root)
            evidence = root / "out" / "evidence"
            capture_snapshot(root, evidence)
            (root / "PROBLEM.md").write_text("MUTATED SOURCE\n", encoding="utf-8")
            result = load_snapshot_inputs(evidence)
            self.assertEqual(result["inputs"]["PROBLEM.md"].read_text(encoding="utf-8"), "Canonical neutral spec\n")

    def test_modified_snapshot_input_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.make_trial(root)
            evidence = root / "out" / "evidence"
            capture_snapshot(root, evidence)
            snapshot = evidence / "inputs" / "PROBLEM.md"
            snapshot.write_text("tampered\n", encoding="utf-8")
            with self.assertRaises(SnapshotConsumptionError):
                load_snapshot_inputs(evidence)

    def test_manifest_cannot_escape_evidence_directory(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.make_trial(root)
            evidence = root / "out" / "evidence"
            capture_snapshot(root, evidence)
            manifest_path = evidence / "snapshot.json"
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            manifest["inputs"][0]["snapshot_path"] = "../../PROBLEM.md"
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            with self.assertRaises(SnapshotConsumptionError):
                load_snapshot_inputs(evidence)

    def test_manifest_rejects_unsafe_logical_input_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.make_trial(root)
            evidence = root / "out" / "evidence"
            capture_snapshot(root, evidence)
            manifest_path = evidence / "snapshot.json"
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            manifest["inputs"][0]["path"] = "../PROBLEM.md"
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            with self.assertRaises(SnapshotConsumptionError):
                load_snapshot_inputs(evidence)


if __name__ == "__main__":
    unittest.main()
