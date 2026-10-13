"""Causal and fail-closed tests for typed authorization semantic consumption."""
import copy

import pytest

from tiannara.domain.models.authorization_semantic_obligations import (
    AuthorizationSemanticConsumptionError,
    consume_authorization_semantics,
)
from tiannara.domain.models.semantic_resolution import (
    ResolutionKind,
    SemanticResolution,
    SemanticResolutionRecord,
    TASKFLOW_MANDATORY_FIELDS,
)


def _record(workspace=None, roles=None):
    values = {
        "authorization.workspace_membership_scope": workspace or {
            "scoped_resources": ["workspace", "project", "task"],
            "scoped_operations": ["read", "write"],
            "cross_scope_denial": {"decision": "reject"},
        },
        "authorization.owner_manager_member_permissions": roles or {
            "roles": ["owner", "manager", "member"],
            "action_permission_matrix": {
                "owner": ["workspace_admin"],
                "manager": ["manage_projects"],
                "member": ["manage_permitted_content"],
            },
        },
    }
    resolutions = []
    for path in TASKFLOW_MANDATORY_FIELDS:
        if path in values:
            resolutions.append(SemanticResolution(
                field_path=path, kind=ResolutionKind.SNAPSHOT,
                value=values[path], source="test:reviewed-fixture",
            ))
        else:
            resolutions.append(SemanticResolution(
                field_path=path, kind=ResolutionKind.UNRESOLVED,
            ))
    return SemanticResolutionRecord(
        graph_id="taskflow-auth-test", graph_hash="a" * 64,
        required_fields=TASKFLOW_MANDATORY_FIELDS,
        resolutions=tuple(resolutions),
    )


def test_consumer_produces_typed_obligations_bound_to_graph():
    record = _record()
    consumed = consume_authorization_semantics(record)
    assert consumed.source_graph_id == record.graph_id
    assert consumed.source_graph_hash == record.graph_hash
    assert consumed.source_paths == (
        "authorization.workspace_membership_scope",
        "authorization.owner_manager_member_permissions",
    )
    assert consumed.workspace_scope["cross_scope_denial"]["decision"] == "reject"
    assert len(consumed.canonical_sha256) == 64


def test_mutating_workspace_semantics_changes_consumption_digest():
    original = _record()
    changed_scope = copy.deepcopy(original.resolutions[1].value)
    # Resolve by path rather than relying on record ordering.
    changed_scope = {
        "scoped_resources": ["workspace", "project", "task", "comment"],
        "scoped_operations": ["read", "write"],
        "cross_scope_denial": {"decision": "reject"},
    }
    changed = _record(workspace=changed_scope)
    assert consume_authorization_semantics(original).canonical_sha256 != (
        consume_authorization_semantics(changed).canonical_sha256
    )


def test_omitted_authorization_semantic_fails_closed():
    record = _record()
    without_workspace = record.model_copy(update={
        "resolutions": tuple(
            item for item in record.resolutions
            if item.field_path != "authorization.workspace_membership_scope"
        )
    })
    with pytest.raises(AuthorizationSemanticConsumptionError, match="unresolved"):
        consume_authorization_semantics(without_workspace)


def test_scalar_authorization_semantic_fails_closed():
    with pytest.raises(AuthorizationSemanticConsumptionError, match="non-empty object"):
        consume_authorization_semantics(_record(workspace={"scoped_resources": "all"}).__class__(
            graph_id="taskflow-auth-test", graph_hash="a" * 64,
            required_fields=TASKFLOW_MANDATORY_FIELDS,
            resolutions=tuple(
                SemanticResolution(
                    field_path=item.field_path,
                    kind=ResolutionKind.SNAPSHOT,
                    value="rbac" if item.field_path == "authorization.workspace_membership_scope" else item.value,
                    source="test:mutated",
                ) if item.field_path in {
                    "authorization.workspace_membership_scope",
                    "authorization.owner_manager_member_permissions",
                } else item
                for item in _record().resolutions
            ),
        ))
