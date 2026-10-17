"""Regression tests for the TaskFlow semantic shape gate.

These tests establish structural rejection only; they do not claim that compiler
backends consume these values or that any TaskFlow implementation is certified.
"""
from __future__ import annotations

import unittest

from tiannara.domain.models.semantic_resolution import (
    ResolutionKind,
    SemanticResolution,
    SemanticResolutionRecord,
    TASKFLOW_MANDATORY_FIELDS,
)
from tiannara.domain.models.taskflow_semantic_contract import (
    IncompleteTaskFlowSemanticContract,
    REQUIRED_VALUE_KEYS,
    validate_taskflow_semantic_contract,
)


def _complete_structural_record() -> SemanticResolutionRecord:
    resolutions = []
    for field_path in TASKFLOW_MANDATORY_FIELDS:
        value = {key: ["explicit-test-value"] for key in REQUIRED_VALUE_KEYS[field_path]}
        resolutions.append(
            SemanticResolution(
                field_path=field_path,
                kind=ResolutionKind.SNAPSHOT,
                value=value,
                source="unit-test-fixture",
            )
        )
    return SemanticResolutionRecord(
        graph_id="test-graph",
        graph_hash="test-hash",
        required_fields=TASKFLOW_MANDATORY_FIELDS,
        resolutions=tuple(resolutions),
    )


class TaskFlowSemanticContractGateTests(unittest.TestCase):
    def test_structurally_complete_record_passes_shape_gate(self) -> None:
        validate_taskflow_semantic_contract(_complete_structural_record())

    def test_missing_required_contract_key_is_rejected(self) -> None:
        record = _complete_structural_record()
        changed = []
        for item in record.resolutions:
            if item.field_path == "sessions.revocation_and_expiry":
                value = dict(item.value)
                value.pop("expiry_policy")
                item = item.model_copy(update={"value": value})
            changed.append(item)
        malformed = record.model_copy(update={"resolutions": tuple(changed)})
        with self.assertRaisesRegex(IncompleteTaskFlowSemanticContract, "expiry_policy"):
            validate_taskflow_semantic_contract(malformed)

    def test_placeholder_required_value_is_rejected(self) -> None:
        record = _complete_structural_record()
        changed = []
        for item in record.resolutions:
            if item.field_path == "sessions.revocation_and_expiry":
                value = dict(item.value)
                value["expiry_policy"] = "TBD"
                item = item.model_copy(update={"value": value})
            changed.append(item)
        malformed = record.model_copy(update={"resolutions": tuple(changed)})
        with self.assertRaisesRegex(IncompleteTaskFlowSemanticContract, "expiry_policy"):
            validate_taskflow_semantic_contract(malformed)

    def test_scalar_semantic_payload_is_rejected(self) -> None:
        record = _complete_structural_record()
        changed = []
        for item in record.resolutions:
            if item.field_path == "authorization.owner_manager_member_permissions":
                item = item.model_copy(update={"value": "owner-manager-member"})
            changed.append(item)
        malformed = record.model_copy(update={"resolutions": tuple(changed)})
        with self.assertRaisesRegex(IncompleteTaskFlowSemanticContract, "structured object"):
            validate_taskflow_semantic_contract(malformed)

    def test_non_authoritative_field_set_is_rejected(self) -> None:
        record = _complete_structural_record().model_copy(
            update={"required_fields": TASKFLOW_MANDATORY_FIELDS[:-1]}
        )
        with self.assertRaisesRegex(IncompleteTaskFlowSemanticContract, "authoritative TaskFlow field set"):
            validate_taskflow_semantic_contract(record)


if __name__ == "__main__":
    unittest.main()
