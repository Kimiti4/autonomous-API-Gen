import pytest
from pydantic import ValidationError

from tiannara.domain.models.semantic_resolution import (
    ResolutionKind,
    SemanticResolution,
    SemanticResolutionRecord,
    UnresolvedSemanticsError,
    require_resolved_semantics,
)


GRAPH_ID = "rg-taskflow-test"
GRAPH_HASH = "a" * 64


def _record(*resolutions, required=("security.authorization",)):
    return SemanticResolutionRecord(
        graph_id=GRAPH_ID,
        graph_hash=GRAPH_HASH,
        required_fields=required,
        resolutions=tuple(resolutions),
    )


def test_missing_mandatory_field_blocks_before_backend_selection():
    record = _record()
    with pytest.raises(UnresolvedSemanticsError, match="security.authorization"):
        require_resolved_semantics(
            record, expected_graph_id=GRAPH_ID, expected_graph_hash=GRAPH_HASH
        )


def test_explicit_unresolved_value_cannot_smuggle_in_default():
    unresolved = SemanticResolution(
        field_path="security.authorization",
        kind=ResolutionKind.UNRESOLVED,
        value=None,
    )
    record = _record(unresolved)
    with pytest.raises(UnresolvedSemanticsError):
        require_resolved_semantics(
            record, expected_graph_id=GRAPH_ID, expected_graph_hash=GRAPH_HASH
        )


def test_snapshot_resolution_requires_value_and_provenance():
    with pytest.raises(ValidationError, match="source provenance"):
        SemanticResolution(
            field_path="security.authorization",
            kind=ResolutionKind.SNAPSHOT,
            value="rbac",
        )


def test_explicit_decision_requires_rationale_and_approval_reference():
    with pytest.raises(ValidationError, match="approval reference"):
        SemanticResolution(
            field_path="deployment.rollout_strategy",
            kind=ResolutionKind.EXPLICIT_DECISION,
            value="rolling",
            source="resolution-review",
            rationale="Chosen for this bounded trial",
        )


def test_resolved_semantics_pass_only_for_the_matching_graph():
    record = _record(
        SemanticResolution(
            field_path="security.authorization",
            kind=ResolutionKind.SNAPSHOT,
            value="rbac",
            source="snapshot:inputs/experiments/taskflow-native/PROBLEM.md#L12",
        )
    )
    require_resolved_semantics(
        record, expected_graph_id=GRAPH_ID, expected_graph_hash=GRAPH_HASH
    )


def test_resolution_record_cannot_authorize_a_different_snapshot():
    record = _record(
        SemanticResolution(
            field_path="security.authorization",
            kind=ResolutionKind.SNAPSHOT,
            value="rbac",
            source="snapshot:inputs/experiments/taskflow-native/PROBLEM.md#L12",
        )
    )
    with pytest.raises(ValueError, match="does not match"):
        require_resolved_semantics(
            record, expected_graph_id=GRAPH_ID, expected_graph_hash="b" * 64
        )


def test_duplicate_resolution_paths_are_rejected():
    item = SemanticResolution(
        field_path="security.authorization",
        kind=ResolutionKind.SNAPSHOT,
        value="rbac",
        source="snapshot:acceptance",
    )
    with pytest.raises(ValidationError, match="duplicate field paths"):
        _record(item, item)


def test_resolution_cannot_introduce_undeclared_fields():
    item = SemanticResolution(
        field_path="deployment.topology",
        kind=ResolutionKind.SNAPSHOT,
        value="modular_monolith",
        source="snapshot:acceptance",
    )
    with pytest.raises(ValidationError, match="undeclared fields"):
        _record(item)


def test_explicit_decision_requires_auditable_approval():
    item = SemanticResolution(
        field_path="security.authorization",
        kind=ResolutionKind.EXPLICIT_DECISION,
        value="rbac",
        source="human-review",
        rationale="TaskFlow mandates role-based access control",
        approval_reference="decision:taskflow-security-001",
    )
    record = _record(item)
    require_resolved_semantics(
        record, expected_graph_id=GRAPH_ID, expected_graph_hash=GRAPH_HASH
    )
