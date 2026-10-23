"""Tests for the strict, versioned TaskFlow semantic payload envelope."""
import pytest
from pydantic import ValidationError

from tiannara.domain.models.semantic_resolution import (
    ResolutionKind,
    SemanticResolution,
    SemanticResolutionRecord,
    TASKFLOW_MANDATORY_FIELDS,
)
from tiannara.domain.models.taskflow_semantic_contract import REQUIRED_VALUE_KEYS
from tiannara.domain.models.taskflow_semantic_payload_v1 import TaskFlowSemanticPayloadV1


PROBLEM_HASH = "a" * 64
ACCEPTANCE_HASH = "b" * 64


def _record(value_for=None):
    value_for = value_for or (
        lambda field: {key: {"decision": "explicitly-reviewed"} for key in REQUIRED_VALUE_KEYS[field]}
    )
    return SemanticResolutionRecord(
        graph_id="rg-taskflow-payload-test",
        graph_hash="c" * 64,
        required_fields=TASKFLOW_MANDATORY_FIELDS,
        resolutions=tuple(
            SemanticResolution(
                field_path=field,
                kind=ResolutionKind.EXPLICIT_DECISION,
                value=value_for(field),
                source="review-fixture:taskflow",
                rationale="Test fixture only; not trusted evidence.",
                approval_reference="fixture-only",
            )
            for field in TASKFLOW_MANDATORY_FIELDS
        ),
    )


def test_complete_resolution_record_builds_bound_v1_payload():
    payload = TaskFlowSemanticPayloadV1.from_resolution_record(
        _record(),
        problem_sha256=PROBLEM_HASH,
        acceptance_sha256=ACCEPTANCE_HASH,
    )
    assert payload.schema_version == "tiannara.taskflow.semantic-payload.v1"
    assert payload.graph_id == "rg-taskflow-payload-test"
    assert set(payload.values) == set(TASKFLOW_MANDATORY_FIELDS)
    assert payload.problem_sha256 == PROBLEM_HASH
    assert payload.acceptance_sha256 == ACCEPTANCE_HASH


def test_nested_placeholder_is_rejected():
    def value_for(field):
        result = {key: {"decision": "explicitly-reviewed"} for key in REQUIRED_VALUE_KEYS[field]}
        result[REQUIRED_VALUE_KEYS[field][0]] = {"nested": ["reviewed", "TBD"]}
        return result

    with pytest.raises(ValueError, match="placeholder value"):
        TaskFlowSemanticPayloadV1.from_resolution_record(
            _record(value_for),
            problem_sha256=PROBLEM_HASH,
            acceptance_sha256=ACCEPTANCE_HASH,
        )


def test_payload_rejects_missing_or_unexpected_semantic_field():
    payload = TaskFlowSemanticPayloadV1.from_resolution_record(
        _record(),
        problem_sha256=PROBLEM_HASH,
        acceptance_sha256=ACCEPTANCE_HASH,
    )
    values = dict(payload.values)
    values.pop(TASKFLOW_MANDATORY_FIELDS[0])
    with pytest.raises(ValidationError, match="exactly the authoritative field set"):
        TaskFlowSemanticPayloadV1(
            graph_id=payload.graph_id,
            graph_hash=payload.graph_hash,
            problem_sha256=payload.problem_sha256,
            acceptance_sha256=payload.acceptance_sha256,
            values=values,
        )


def test_payload_rejects_non_sha256_snapshot_hashes():
    with pytest.raises(ValidationError, match="problem_sha256"):
        TaskFlowSemanticPayloadV1.from_resolution_record(
            _record(),
            problem_sha256="not-a-hash",
            acceptance_sha256=ACCEPTANCE_HASH,
        )


def test_unresolved_record_cannot_be_serialized_as_a_payload():
    record = _record()
    unresolved = record.model_copy(update={
        "resolutions": tuple(
            item.model_copy(update={"kind": ResolutionKind.UNRESOLVED, "value": None, "source": None, "rationale": None, "approval_reference": None})
            if item.field_path == TASKFLOW_MANDATORY_FIELDS[0] else item
            for item in record.resolutions
        )
    })
    with pytest.raises(ValueError, match="unresolved fields"):
        TaskFlowSemanticPayloadV1.from_resolution_record(
            unresolved,
            problem_sha256=PROBLEM_HASH,
            acceptance_sha256=ACCEPTANCE_HASH,
        )


def test_empty_collections_are_allowed_when_reviewed_and_bound():
    def value_for(field):
        result = {key: {"decision": "explicitly-reviewed"} for key in REQUIRED_VALUE_KEYS[field]}
        result[REQUIRED_VALUE_KEYS[field][0]] = []
        return result

    payload = TaskFlowSemanticPayloadV1.from_resolution_record(
        _record(value_for),
        problem_sha256=PROBLEM_HASH,
        acceptance_sha256=ACCEPTANCE_HASH,
    )
    assert payload.values[TASKFLOW_MANDATORY_FIELDS[0]][REQUIRED_VALUE_KEYS[TASKFLOW_MANDATORY_FIELDS[0]][0]] == []

def test_payload_rejects_malformed_requirement_graph_hash():
    record = _record()
    malformed = record.model_copy(update={"graph_hash": "not-a-hash"})
    with pytest.raises(ValidationError, match="graph_hash"):
        TaskFlowSemanticPayloadV1.from_resolution_record(
            malformed,
            problem_sha256=PROBLEM_HASH,
            acceptance_sha256=ACCEPTANCE_HASH,
        )

