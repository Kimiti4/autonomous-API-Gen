"""Minimum typed-shape validation for mandatory TaskFlow semantics.

This gate rejects scalar and placeholder values; it does not infer decisions or
claim that any compiler consumes the resulting contract.
"""
from collections.abc import Mapping
from typing import Any
from .semantic_resolution import TASKFLOW_MANDATORY_FIELDS, SemanticResolutionRecord, ResolutionKind, resolutions_by_field

REQUIRED_VALUE_KEYS = {
"identity.registration_and_authentication": ("registration_fields", "credential_lifecycle"),
"authorization.workspace_membership_scope": ("scoped_resources", "scoped_operations", "cross_scope_denial"),
"authorization.owner_manager_member_permissions": ("roles", "action_permission_matrix"),
"data.workspace_project_task_relationships": ("entities", "relationships", "integrity_invariants"),
"data.comments_and_activity_history": ("comment_operations", "activity_event_schema", "visibility_rules"),
"tasks.assignment_status_priority_and_due_dates": ("status_values", "priority_values", "allowed_transitions", "due_date_rules", "assignment_rules"),
"tasks.archive_visibility": ("archivable_resource_types", "archive_restore_rules", "active_query_visibility"),
"sessions.revocation_and_expiry": ("expiry_policy", "refresh_policy", "revocation_behavior"),
"api.request_response_and_error_contracts": ("operations", "request_schemas", "response_schemas", "error_contract"),
"frontend.required_interactions_and_state_transitions": ("screens_or_views", "interaction_flows", "ui_state_transitions"),
"persistence.consistency_and_atomic_mutations": ("consistency_guarantees", "atomic_mutations", "conflict_and_rollback_rules"),
"operations.idempotency_and_unique_effect_identity": ("idempotent_operations", "key_scope_and_retention", "effect_identity_rules"),
"operations.health_readiness_and_audit_evidence": ("health_conditions", "readiness_conditions", "audit_event_schema"),
"deployment.reproducible_execution_environment": ("runtime_inputs", "configuration_contract", "reproducibility_checks"),
"verification.required_capability_and_negative_case_mapping": ("capability_test_mapping", "negative_case_test_mapping", "evidence_requirements"),
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
    if isinstance(value, (list, tuple, set)):
        return bool(value) and all(_has_content(v) for v in value)
    return True

def validate_taskflow_semantic_contract(record: SemanticResolutionRecord) -> None:
    if record.required_fields != TASKFLOW_MANDATORY_FIELDS:
        raise IncompleteTaskFlowSemanticContract("semantic record must use the authoritative TaskFlow field set")
    by_field = resolutions_by_field(record)
    issues = []
    for path in TASKFLOW_MANDATORY_FIELDS:
        item = by_field.get(path)
        if item is None or item.kind is ResolutionKind.UNRESOLVED:
            continue
        if not isinstance(item.value, Mapping):
            issues.append(f"{path}: value must be a structured object")
            continue
        missing = [key for key in REQUIRED_VALUE_KEYS[path] if key not in item.value or not _has_content(item.value[key])]
        if missing:
            issues.append(f"{path}: missing or placeholder contract keys: {', '.join(missing)}")
    if issues:
        raise IncompleteTaskFlowSemanticContract("TaskFlow semantic contract is structurally incomplete: " + "; ".join(issues))
