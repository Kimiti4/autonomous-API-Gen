import pytest

from app.engine.generation_scope import GenerationScope
from app.engine.project_scope import ProjectScope
from app.engine.scope_authorization import MutationIntent, ScopeViolation
from app.engine.work_scope import WorkScope, validate_work_scope


def test_new_frontend_work_scope_is_valid():
    scope = WorkScope.create(ProjectScope.create_new(), GenerationScope.FRONTEND_ONLY)
    assert validate_work_scope(scope) is scope
    assert scope.generation.allows("frontend")


def test_existing_backend_maintenance_scope_is_valid():
    scope = WorkScope.create(
        ProjectScope.maintain_existing(),
        GenerationScope.BACKEND_ONLY,
    )
    assert validate_work_scope(scope) is scope
    assert scope.project.intent.value == "maintain"


def test_existing_api_improvement_scope_is_valid():
    scope = WorkScope.create(
        ProjectScope.improve_existing(),
        GenerationScope.API_CONTRACT_ONLY,
    )
    authorized = scope.authorize(
        (MutationIntent("api_contract", "edit", "openapi.yaml"),)
    )
    assert authorized[0].surface == "api_contract"


def test_combined_scope_blocks_unauthorized_surface():
    scope = WorkScope.create(
        ProjectScope.improve_existing(),
        GenerationScope.FRONTEND_ONLY,
    )
    with pytest.raises(ScopeViolation):
        scope.authorize(
            (
                MutationIntent("frontend", "edit", "src/App.tsx"),
                MutationIntent("backend", "edit", "api/app.py"),
            )
        )


def test_invalid_work_scope_fails_closed():
    with pytest.raises(ValueError, match="invalid-work-scope"):
        validate_work_scope("frontend")
