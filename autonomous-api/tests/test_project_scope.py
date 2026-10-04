import pytest

from app.engine.project_scope import (
    ChangeKind,
    ProjectIntent,
    ProjectScope,
    validate_project_scope,
)


@pytest.mark.parametrize(
    "scope",
    (
        ProjectScope.create_new(),
        ProjectScope.maintain_existing(),
        ProjectScope.improve_existing(),
    ),
)
def test_supported_project_intents_validate(scope):
    assert validate_project_scope(scope) is scope


def test_create_requires_new_project():
    with pytest.raises(ValueError, match="create-requires-new-project"):
        validate_project_scope(ProjectScope(ProjectIntent.CREATE, ChangeKind.EXISTING_PROJECT))


def test_maintenance_requires_existing_project():
    with pytest.raises(ValueError, match="existing-project-intent"):
        validate_project_scope(ProjectScope(ProjectIntent.MAINTAIN, ChangeKind.NEW_PROJECT))


def test_improvement_requires_existing_project():
    with pytest.raises(ValueError, match="existing-project-intent"):
        validate_project_scope(ProjectScope(ProjectIntent.IMPROVE, ChangeKind.NEW_PROJECT))


def test_invalid_scope_fails_closed():
    with pytest.raises(ValueError, match="invalid-project-scope"):
        validate_project_scope("improve");
