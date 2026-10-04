import pytest

from app.engine.generation_scope import GenerationScope, validate_scope
from app.engine.project_scope import ProjectScope
from app.observation.contracts.work_scope import WorkScopeDeclared


def test_work_scope_event_payload_is_explicit_and_serializable():
    project = ProjectScope.create_new()
    generation = validate_scope(GenerationScope.FRONTEND_ONLY)
    payload = WorkScopeDeclared(
        projectIntent=project.intent.value,
        projectKind=project.change_kind.value,
        generationScope=generation.scope.value,
        allowedSurfaces=["frontend"],
        preservedSurfaces=["backend", "api_contract"],
    )
    assert payload.model_dump(mode="json")["generationScope"] == "frontend_only"


def test_work_scope_event_rejects_missing_identity():
    with pytest.raises(ValueError):
        WorkScopeDeclared(
            projectIntent="",
            projectKind="new_project",
            generationScope="frontend_only",
            allowedSurfaces=[],
            preservedSurfaces=[],
        )
