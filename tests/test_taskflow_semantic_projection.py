import pytest
from pydantic import ValidationError

from tiannara.application.intent.schemas import TaskFlowSemanticProjection
from tiannara.domain.models.system_model import RequirementsReference, SystemModel


GRAPH_ID = "rg-taskflow-projection"
GRAPH_HASH = "f" * 64


def _model(values):
    return SystemModel(
        system_name="taskflow",
        problem_statement="Canonical TaskFlow snapshot",
        requirements_ref=RequirementsReference(
            graph_id=GRAPH_ID,
            graph_hash=GRAPH_HASH,
        ),
        extensions={"taskflow_semantic_values": values},
    )


def test_projection_contract_preserves_exact_semantic_values():
    values = {
        "authorization.workspace_membership_scope": {
            "scope": "workspace_membership",
            "fail_closed": True,
        },
        "sessions.revocation_and_expiry": {
            "revocation_supported": True,
            "expiry_policy": "explicitly-reviewed",
        },
    }

    projection = TaskFlowSemanticProjection(
        system_model=_model(values),
        projected_values=values,
    )

    assert projection.system_model.extensions["taskflow_semantic_values"] == values
    assert projection.projected_values == values


def test_projection_rejects_values_not_preserved_in_system_model():
    reviewed = {"authorization.workspace_membership_scope": {"scope": "workspace"}}
    altered = {"authorization.workspace_membership_scope": {"scope": "global"}}

    with pytest.raises(ValidationError, match="must preserve the exact projected semantic values"):
        TaskFlowSemanticProjection(
            system_model=_model(altered),
            projected_values=reviewed,
        )


def test_projection_rejects_blank_semantic_paths():
    with pytest.raises(ValidationError, match="blank paths"):
        TaskFlowSemanticProjection(
            system_model=_model({"": "value"}),
            projected_values={"": "value"},
        )
