from __future__ import annotations

import json
from pathlib import Path
import sys
import unittest

TRIAL_DIR = Path(__file__).resolve().parents[1]
ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(TRIAL_DIR))
sys.path.insert(0, str(ROOT))

from provider_free.isr_profile import build_taskflow_profile  # noqa: E402


ACCEPTANCE = json.loads(
    (ROOT / "golden-projects" / "taskflow" / "ACCEPTANCE.json").read_text(encoding="utf-8")
)
PROBLEM = (TRIAL_DIR / "PROBLEM.md").read_text(encoding="utf-8")


class DeterministicTaskFlowProfileTests(unittest.TestCase):
    def test_same_inputs_produce_same_semantic_isr_hash_and_profile(self) -> None:
        first = build_taskflow_profile(PROBLEM, ACCEPTANCE).as_dict()
        second = build_taskflow_profile(PROBLEM, ACCEPTANCE).as_dict()
        self.assertEqual(first["isr_sha256"], second["isr_sha256"])
        self.assertEqual(first, second)

    def test_every_capability_has_one_stable_requirement_trace(self) -> None:
        result = build_taskflow_profile(PROBLEM, ACCEPTANCE).as_dict()
        traces = result["traceability"]["capabilities"]
        self.assertEqual(len(traces), len(ACCEPTANCE["required_capabilities"]))
        self.assertEqual(len({item["requirement_id"] for item in traces}), len(traces))
        self.assertEqual(len({item["capability_id"] for item in traces}), len(traces))
        self.assertEqual(
            {item["source_name"] for item in traces},
            set(ACCEPTANCE["required_capabilities"]),
        )

    def test_only_explicit_problem_nouns_become_schema_unknown_entities(self) -> None:
        result = build_taskflow_profile(PROBLEM, ACCEPTANCE).as_dict()
        entities = result["traceability"]["entities"]
        self.assertEqual(
            {item["entity_name"] for item in entities},
            {"User", "Workspace", "Project", "Task", "Comment", "ActivityHistory", "Session"},
        )
        self.assertTrue(all(item["schema_status"] == "UNKNOWN" for item in entities))
        module = result["isr"]["system"]["modules"][0]
        self.assertEqual(len(module["entities"]), len(entities))
        self.assertTrue(all(not entity["fields"] and not entity["relationships"] for entity in module["entities"]))

    def test_explicit_problem_obligations_are_source_traced_and_unknown(self) -> None:
        result = build_taskflow_profile(PROBLEM, ACCEPTANCE).as_dict()
        obligations = result["traceability"]["problem_obligations"]
        self.assertEqual(len(obligations), 15)
        self.assertEqual(len({item["requirement_id"] for item in obligations}), 15)
        self.assertTrue(all(item["status"] == "UNKNOWN" for item in obligations))
        self.assertTrue(all(item["source_line"] > 0 for item in obligations))
        self.assertTrue(all(item["statement"] in PROBLEM for item in obligations))

    def test_quality_gates_and_negative_cases_remain_unknown(self) -> None:
        result = build_taskflow_profile(PROBLEM, ACCEPTANCE).as_dict()
        self.assertEqual(
            len(result["traceability"]["quality_gates"]),
            sum(ACCEPTANCE["quality_gates"].values()),
        )
        self.assertEqual(
            len(result["traceability"]["negative_cases"]),
            len(ACCEPTANCE["negative_cases"]),
        )
        self.assertTrue(all(x["status"] == "UNKNOWN" for x in result["traceability"]["quality_gates"]))
        self.assertTrue(all(x["status"] == "UNKNOWN" for x in result["traceability"]["negative_cases"]))

    def test_underspecified_semantics_block_generation(self) -> None:
        result = build_taskflow_profile(PROBLEM, ACCEPTANCE).as_dict()
        self.assertTrue(result["isr_structurally_valid"])
        self.assertFalse(result["generation_allowed"])
        self.assertFalse(result["certified"])
        self.assertFalse(result["provider_required"])
        self.assertEqual(result["network_calls"], 0)
        self.assertTrue(result["assumptions"])
        self.assertTrue(result["generation_blockers"])

    def test_duplicate_or_malformed_contract_entries_fail_closed(self) -> None:
        invalid = dict(ACCEPTANCE)
        invalid["required_capabilities"] = ACCEPTANCE["required_capabilities"] + [ACCEPTANCE["required_capabilities"][0]]
        with self.assertRaisesRegex(ValueError, "duplicates"):
            build_taskflow_profile(PROBLEM, invalid)


if __name__ == "__main__":
    unittest.main()
