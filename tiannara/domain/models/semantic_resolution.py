"""Fail-closed semantic resolution records for native ISR construction.

This module is deliberately separate from SystemModel so legacy payloads,
serialization, and content hashes remain unchanged. Compiler entry points must
call require_resolved_semantics before constructing a SystemModel or selecting
a backend.
"""
from __future__ import annotations

import enum
from typing import Mapping

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ResolutionKind(str, enum.Enum):
    """How a mandatory semantic obtained its current value."""

    SNAPSHOT = "snapshot"
    EXPLICIT_DECISION = "explicit_decision"
    UNRESOLVED = "unresolved"


class SemanticResolution(BaseModel):
    """One semantic field and auditable evidence for its resolution."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    field_path: str = Field(min_length=1)
    kind: ResolutionKind
    value: object | None = None
    source: str | None = None
    rationale: str | None = None
    approval_reference: str | None = None

    @model_validator(mode="after")
    def validate_resolution_evidence(self) -> "SemanticResolution":
        if self.kind is ResolutionKind.UNRESOLVED:
            if self.value is not None:
                raise ValueError("unresolved semantics must not carry an assumed value")
            return self
        if self.value is None:
            raise ValueError("resolved semantics require an explicit value")
        if not self.source or not self.source.strip():
            raise ValueError("resolved semantics require source provenance")
        if self.kind is ResolutionKind.EXPLICIT_DECISION:
            if not self.rationale or not self.rationale.strip():
                raise ValueError("explicit decisions require a rationale")
            if not self.approval_reference or not self.approval_reference.strip():
                raise ValueError("explicit decisions require an approval reference")
        return self


class SemanticResolutionRecord(BaseModel):
    """Resolution ledger bound to a specific immutable requirement graph."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: str = "semantic-resolution.v1"
    graph_id: str = Field(min_length=1)
    graph_hash: str = Field(min_length=1)
    required_fields: tuple[str, ...]
    resolutions: tuple[SemanticResolution, ...]

    @model_validator(mode="after")
    def validate_unique_and_complete_index(self) -> "SemanticResolutionRecord":
        if len(self.required_fields) != len(set(self.required_fields)):
            raise ValueError("required_fields contains duplicates")
        paths = [item.field_path for item in self.resolutions]
        if len(paths) != len(set(paths)):
            raise ValueError("resolutions contains duplicate field paths")
        unexpected = set(paths) - set(self.required_fields)
        if unexpected:
            raise ValueError(
                "resolution record contains undeclared fields: "
                + ", ".join(sorted(unexpected))
            )
        return self

    def unresolved_fields(self) -> tuple[str, ...]:
        by_path = {item.field_path: item for item in self.resolutions}
        return tuple(
            path
            for path in self.required_fields
            if path not in by_path
            or by_path[path].kind is ResolutionKind.UNRESOLVED
        )


class UnresolvedSemanticsError(ValueError):
    """Raised when a compiler attempts to proceed with unresolved mandatory fields."""

    def __init__(self, fields: tuple[str, ...]) -> None:
        self.fields = fields
        super().__init__(
            "generation blocked before SystemModel construction/backend selection; "
            "unresolved mandatory semantics: " + ", ".join(fields)
        )


def require_resolved_semantics(
    record: SemanticResolutionRecord,
    *,
    expected_graph_id: str,
    expected_graph_hash: str,
) -> None:
    """Hard gate to call before model construction and backend selection.

    The graph identity binding prevents a resolution ledger for one snapshot
    from authorizing compilation of a different requirement graph.
    """
    if record.graph_id != expected_graph_id or record.graph_hash != expected_graph_hash:
        raise ValueError("semantic resolution record does not match the active requirement graph")
    unresolved = record.unresolved_fields()
    if unresolved:
        raise UnresolvedSemanticsError(unresolved)


def resolutions_by_field(
    record: SemanticResolutionRecord,
) -> Mapping[str, SemanticResolution]:
    """Return a read-only-by-convention field index for downstream model builders."""
    return {item.field_path: item for item in record.resolutions}


# Compiler-owned TaskFlow contract. Keep this outside SystemModel so legacy
# serialization and ISR content hashes remain unchanged.
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


def build_initial_resolution_record(graph) -> SemanticResolutionRecord:
    """Build an explicit unresolved ledger for this exact requirement graph."""
    return SemanticResolutionRecord(
        graph_id=graph.graph_id,
        graph_hash=graph.content_hash(),
        required_fields=TASKFLOW_MANDATORY_FIELDS,
        resolutions=tuple(
            SemanticResolution(field_path=path, kind=ResolutionKind.UNRESOLVED)
            for path in TASKFLOW_MANDATORY_FIELDS
        ),
    )


def require_taskflow_semantics(graph, record: SemanticResolutionRecord) -> None:
    """Enforce the compiler-owned TaskFlow field set and graph binding."""
    if record.required_fields != TASKFLOW_MANDATORY_FIELDS:
        raise ValueError(
            "semantic resolution record does not match the authoritative TaskFlow "
            "mandatory-field contract"
        )
    require_resolved_semantics(
        record,
        expected_graph_id=graph.graph_id,
        expected_graph_hash=graph.content_hash(),
    )
