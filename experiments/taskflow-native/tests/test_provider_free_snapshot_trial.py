from __future__ import annotations

import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

TRIAL_DIR = Path(__file__).resolve().parents[1]
ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(TRIAL_DIR))
sys.path.insert(0, str(ROOT))

import run_snapshot_trial  # noqa: E402


class ProviderFreeSnapshotTrialTests(unittest.TestCase):
    def test_snapshot_intake_emits_non_certifying_ledger_without_provider(self) -> None:
        acceptance = {
            "project_id": "TASKFLOW-GOLDEN-001",
            "required_capabilities": ["authentication", "workspace-tenancy"],
            "quality_gates": {"security": True, "build": True},
            "negative_cases": ["cross_workspace_read"],
            "certification_rule": "Unknown evidence blocks certification.",
        }
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            problem_path = root / "PROBLEM.md"
            acceptance_path = root / "ACCEPTANCE.json"
            evidence_dir = root / "evidence"
            problem_path.write_text("Build a multi-user task-management app.", encoding="utf-8")
            acceptance_path.write_text(json.dumps(acceptance), encoding="utf-8")
            snapshot = {
                "contract_sha256": "a" * 64,
                "inputs": {
                    "experiments/taskflow-native/PROBLEM.md": problem_path,
                    "golden-projects/taskflow/ACCEPTANCE.json": acceptance_path,
                },
            }
            with (
                patch.object(run_snapshot_trial, "load_snapshot_inputs", return_value=snapshot),
                patch.dict(os.environ, {"TIANNARA_LLM_BASE_URL": "", "TIANNARA_LLM_MODEL": ""}),
            ):
                code = run_snapshot_trial.run(evidence_dir, timeout_seconds=1)

            self.assertEqual(code, 2)
            report = json.loads((evidence_dir / "live-attempt.json").read_text(encoding="utf-8"))
            ledger = json.loads((evidence_dir / "provider-free-analysis.json").read_text(encoding="utf-8"))
            self.assertEqual(report["verdict"], "BLOCKED")
            self.assertEqual(report["provider_free_analysis"]["contract_sha256"], ledger["contract_sha256"])
            self.assertFalse(report["provider_free_analysis"]["certified"])
            self.assertFalse(ledger["certified"])
            self.assertEqual(ledger["network_calls"], 0)
            self.assertIn("provider-free-analysis.json", report["evidence"])
            self.assertIn("no deterministic TaskFlow ISR builder", report["next_blocker"])


if __name__ == "__main__":
    unittest.main()
