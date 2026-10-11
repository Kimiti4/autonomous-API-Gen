"""Authoritative mandatory semantic contract for the TaskFlow native trial.

The contract is compiler-owned. Callers cannot weaken it by supplying a smaller
required_fields list. These are semantic obligations, not implementation choices.
"""
from __future__ import annotations

from tiannara.domain.models.requirement_graph import RequirementGraph
from tiannara.domain.models.semantic_resolution import (
    ResolutionKind,
    SemanticResolution,
    SemanticResolutionRecord,
)

TASKFLOW_MANDATORY_FIELDS: tuple[str, ...] = (
    "identity.registration_and_authentication",
    "authorization.workspace_membership_scope",
    "authorization.owner_manager_member_permissions",
    "data.workspace_project_task_relationships",
    "data.comments_and_activity_history",
    "tasks.assignment_status_priority_and_due_dates",
    "tasks.archive_visibility",
    "sessions.revocation_and_expiry",
    "api.request_response_and_error_contracts",
    "frontend.required_interactions_and_state_transitions",
    "persistence.consistency_and_atomic_mutations",
    "operations.idempotency_and_unique_effect_identity",
    "operations.health_readiness_and_audit_evidence",
    "deployment.reproducible_execution_environment",
    "verification.required_capability_and_negative_case_mapping",
)


def build_initial_resolution_record(graph: RequirementGraph) -> SemanticResolutionRecord:
    """Create a graph-bound ledger with every mandatory field explicitly unresolved."""
    return SemanticResolutionRecord(
        graph_id=graph.graph_id,
        graph_hash=graph.content_hash(),
        required_fields=TASKFLOW_MANDATORY_FIELDS,
        resolutions=tuple(
            SemanticResolution(field_path=path, kind=ResolutionKind.UNRESOLVED)
            for path in TASKFLOW_MANDATORY_FIELDS
        ),
    )


def require_taskflow_semantics(
    graph: RequirementGraph,
    record: SemanticResolutionRecord,
) -> None:
    """Enforce the authoritative field set and bind it to the active graph."""
    if record.required_fields != TASKFLOW_MANDATORY_FIELDS:
        raise ValueError(
            "semantic resolution record does not match the authoritative TaskFlow "
            "mandatory-field contract"
        )
    from tiannara.domain.models.semantic_resolution import require_resolved_semantics

    require_resolved_semantics(
        record,
        expected_graph_id=graph.graph_id,
        expected_graph_hash=graph.content_hash(),
    )
