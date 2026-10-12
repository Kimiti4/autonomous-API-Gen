"""Fail-closed JSON-shape validation for mandatory TaskFlow semantics.

This checks the minimum typed structure needed before projection. It does not
resolve policy choices, validate every nested domain rule, or prove consumption.
"""
from collections.abc import Mapping
from typing import Any

from .semantic_resolution import (
    TASKFLOW_MANDATORY_FIELDS,
    ResolutionKind,
    SemanticResolutionRecord,
    resolutions_by_field,
)

# Required key names are part of the compiler-owned contract. Expected JSON
# shapes are structural types only; they intentionally do not invent policy
# values such as timeout durations, role permissions, or retention periods.
REQUIRED_VALUE_SHAPES = {
    "identity.registration_and_authentication": {
        "registration_fields": "array",
        "credential_lifecycle": "object",
    },
    "authorization.workspace_membership_scope": {
        "scoped_resources": "array",
        "scoped_operations": "array",
        "cross_scope_denial": "object",
    },
    "authorization.owner_manager_member_permissions": {
        "roles": "array",
        "action_permission_matrix": "object",
    },
    "data.workspace_project_task_relationships": {
        "entities": "array",
        "relationships": "array",
        "integrity_invariants": "array",
    },
    "data.comments_and_activity_history": {
        "comment_operations": "array",
        "activity_event_schema": "object",
        "visibility_rules": "object",
    },
    "tasks.assignment_status_priority_and_due_dates": {
        "status_values": "array",
        "priority_values": "array",
        "allowed_transitions": "array",
        "due_date_rules": "object",
        "assignment_rules": "object",
    },
    "tasks.archive_visibility": {
        "archivable_resource_types": "array",
        "archive_restore_rules": "object",
        "active_query_visibility": "object",
    },
    "sessions.revocation_and_expiry": {
        "expiry_policy": "object",
        "refresh_policy": "object",
        "revocation_behavior": "object",
    },
    "api.request_response_and_error_contracts": {
        "operations": "array",
        "request_schemas": "object",
        "response_schemas": "object",
        "error_contract": "object",
    },
    "frontend.required_interactions_and_state_transitions": {
        "screens_or_views": "array",
        "interaction_flows": "array",
        "ui_state_transitions": "array",
    },
    "persistence.consistency_and_atomic_mutations": {
        "consistency_guarantees": "array",
        "atomic_mutations": "array",
        "conflict_and_rollback_rules": "object",
    },
    "operations.idempotency_and_unique_effect_identity": {
        "idempotent_operations": "array",
        "key_scope_and_retention": "object",
        "effect_identity_rules": "object",
    },
    "operations.health_readiness_and_audit_evidence": {
        "health_conditions": "array",
        "readiness_conditions": "array",
        "audit_event_schema": "object",
    },
    "deployment.reproducible_execution_environment": {
        "runtime_inputs": "array",
        "configuration_contract": "object",
        "reproducibility_checks": "array",
    },
    "verification.required_capability_and_negative_case_mapping": {
        "capability_test_mapping": "object",
        "negative_case_test_mapping": "object",
        "evidence_requirements": "object",
    },
}
REQUIRED_VALUE_KEYS = {
    path: tuple(shapes)
    for path, shapes in REQUIRED_VALUE_SHAPES.items()
}
_PLACEHOLDERS = {"", "unknown", "unresolved", "tbd", "todo", "n/a", "not specified"}


class IncompleteTaskFlowSemanticContract(ValueError):
    """Resolved ledger has not met the minimum typed contract shape."""


def _has_content(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return value.strip().casefold() not in _PLACEHOLDERS
    if isinstance(value, Mapping):
        return bool(value) and all(_has_content(v) for v in value.values())
    if isinstance(value, (list, tuple)):
        return bool(value) and all(_has_content(v) for v in value)
    return True


def _matches_shape(value: Any, expected: str) -> bool:
    if expected == "object":
        return isinstance(value, Mapping) and bool(value)
    if expected == "array":
        return isinstance(value, list) and bool(value)
    return False


def validate_taskflow_semantic_contract(record: SemanticResolutionRecord) -> None:
    if record.required_fields != TASKFLOW_MANDATORY_FIELDS:
        raise IncompleteTaskFlowSemanticContract(
            "semantic record must use the authoritative TaskFlow field set"
        )
    by_field = resolutions_by_field(record)
    issues = []
    for path in TASKFLOW_MANDATORY_FIELDS:
        item = by_field.get(path)
        if item is None or item.kind is ResolutionKind.UNRESOLVED:
            continue
        if not isinstance(item.value, Mapping):
            issues.append(f"{path}: value must be a structured object")
            continue
        missing = []
        wrong_shape = []
        for key, expected_shape in REQUIRED_VALUE_SHAPES[path].items():
            value = item.value.get(key)
            if key not in item.value or not _has_content(value):
                missing.append(key)
            elif not _matches_shape(value, expected_shape):
                wrong_shape.append(f"{key} (expected non-empty {expected_shape})")
        if missing:
            issues.append(f"{path}: missing or placeholder contract keys: {', '.join(missing)}")
        if wrong_shape:
            issues.append(f"{path}: invalid contract value shape: {', '.join(wrong_shape)}")
    if issues:
        raise IncompleteTaskFlowSemanticContract(
            "TaskFlow semantic contract is structurally incomplete: " + "; ".join(issues)
        )
