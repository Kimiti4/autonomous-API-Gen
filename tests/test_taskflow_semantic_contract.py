"""Negative and shape tests for the mandatory TaskFlow semantic contract."""
import pytest
from tiannara.domain.models.semantic_resolution import ResolutionKind, SemanticResolution, SemanticResolutionRecord, TASKFLOW_MANDATORY_FIELDS
from tiannara.domain.models.taskflow_semantic_contract import IncompleteTaskFlowSemanticContract, REQUIRED_VALUE_KEYS, REQUIRED_VALUE_SHAPES, validate_taskflow_semantic_contract

def _record(value_for):
    return SemanticResolutionRecord(
        graph_id="taskflow-contract-test",
        graph_hash="a" * 64,
        required_fields=TASKFLOW_MANDATORY_FIELDS,
        resolutions=tuple(SemanticResolution(field_path=path, kind=ResolutionKind.SNAPSHOT, value=value_for(path), source="reviewed-input:test-fixture") for path in TASKFLOW_MANDATORY_FIELDS),
    )

def _complete_shape(path):
    return {key: ([{"decision": "explicitly-defined"}] if shape == "array" else {"decision": "explicitly-defined"}) for key, shape in REQUIRED_VALUE_SHAPES[path].items()}

def test_scalar_values_cannot_satisfy_complex_mandatory_semantics():
    with pytest.raises(IncompleteTaskFlowSemanticContract, match="structured object"):
        validate_taskflow_semantic_contract(_record(lambda _path: "rbac"))

def test_missing_field_specific_contract_keys_are_rejected():
    def incomplete(path):
        return {REQUIRED_VALUE_KEYS[path][0]: {"decision": "defined"}}
    with pytest.raises(IncompleteTaskFlowSemanticContract, match="missing or placeholder|invalid contract value shape"):
        validate_taskflow_semantic_contract(_record(incomplete))

def test_wrong_container_type_is_rejected_even_when_nonempty():
    def wrong_shape(path):
        value = _complete_shape(path)
        for key, shape in REQUIRED_VALUE_SHAPES[path].items():
            if shape == "array":
                value[key] = {"looks": "non-empty but is not an array"}
                break
        return value

    with pytest.raises(IncompleteTaskFlowSemanticContract, match="invalid contract value shape"):
        validate_taskflow_semantic_contract(_record(wrong_shape))


def test_unknown_or_tbd_values_are_rejected():
    def placeholder(path):
        return {key: ([{"decision": "TBD"}] if shape == "array" else {"decision": "TBD"}) for key, shape in REQUIRED_VALUE_SHAPES[path].items()}
    with pytest.raises(IncompleteTaskFlowSemanticContract, match="missing or placeholder"):
        validate_taskflow_semantic_contract(_record(placeholder))

def test_each_mandatory_field_requires_its_declared_shape():
    validate_taskflow_semantic_contract(_record(_complete_shape))

def test_authoritative_field_set_cannot_be_replaced_with_subset():
    record = SemanticResolutionRecord(graph_id="taskflow-contract-test", graph_hash="a" * 64, required_fields=("identity.registration_and_authentication",), resolutions=())
    with pytest.raises(IncompleteTaskFlowSemanticContract, match="authoritative TaskFlow"):
        validate_taskflow_semantic_contract(record)
