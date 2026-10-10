from __future__ import annotations

import json
from pathlib import Path
import unittest

from experiments.taskflow_native.provider_free.requirements import analyze_acceptance


ROOT = Path(__file__).resolve().parents[3]
ACCEPTANCE_PATH = ROOT / "golden-projects" / "taskflow" / "ACCEPTANCE.json"


class ProviderFreeRequirementAnalysisTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.acceptance = json.loads(ACCEPTANCE_PATH.read_text(encoding="utf-8"))

    def test_canonical_contract_is_analyzed_without_claiming_certification(self) -> None:
        result = analyze_acceptance(self.acceptance).as_dict()
        capabilities = [
            item for item in result["requirements"] if item["kind"] == "capability"
        ]
        gates = [
            item for item in result["requirements"] if item["kind"] == "quality_gate"
        ]
        negative_cases = [
            item for item in result["requirements"] if item["kind"] == "negative_case"
        ]

        self.assertEqual(result["project_id"], self.acceptance["project_id"])
        self.assertEqual(len(capabilities), len(self.acceptance["required_capabilities"]))
        self.assertEqual(len(gates), sum(self.acceptance["quality_gates"].values()))
        self.assertEqual(len(negative_cases), len(self.acceptance["negative_cases"]))
        self.assertTrue(all(item["status"] == "unsupported" for item in capabilities))
        self.assertTrue(all(item["status"] == "unknown" for item in gates + negative_cases))
        self.assertFalse(result["certified"])
        self.assertFalse(result["provider_required"])
        self.assertEqual(result["network_calls"], 0)

    def test_registered_capability_must_exist_in_contract(self) -> None:
        with self.assertRaisesRegex(ValueError, "absent from the contract"):
            analyze_acceptance(
                self.acceptance, supported_capabilities={"imaginary-capability"}
            )

    def test_only_explicitly_registered_capabilities_are_supported(self) -> None:
        name = self.acceptance["required_capabilities"][0]
        result = analyze_acceptance(
            self.acceptance, supported_capabilities={name}
        ).as_dict()
        item = next(
            item for item in result["requirements"]
            if item["kind"] == "capability" and item["name"] == name
        )
        self.assertEqual(item["status"], "supported")
        self.assertFalse(result["certified"])

    def test_duplicate_capabilities_fail_closed(self) -> None:
        invalid = dict(self.acceptance)
        invalid["required_capabilities"] = (
            self.acceptance["required_capabilities"][:1] * 2
        )
        with self.assertRaisesRegex(ValueError, "duplicates"):
            analyze_acceptance(invalid)

    def test_contract_digest_and_requirement_ids_are_reproducible(self) -> None:
        first = analyze_acceptance(self.acceptance).as_dict()
        second = analyze_acceptance(self.acceptance).as_dict()
        self.assertEqual(first["contract_sha256"], second["contract_sha256"])
        self.assertEqual(
            [item["requirement_id"] for item in first["requirements"]],
            [item["requirement_id"] for item in second["requirements"]],
        )


if __name__ == "__main__":
    unittest.main()
