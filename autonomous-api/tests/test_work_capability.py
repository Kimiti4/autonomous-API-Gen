import pytest
from app.engine.generation_scope import GenerationScope
from app.engine.project_scope import ProjectScope
from app.engine.scope_authorization import MutationIntent, ScopeViolation
from app.engine.work_mode import WorkMode
from app.engine.work_capability import WorkCapabilityContract, validate_work_capability


def test_combines_project_mode_and_surface():
    c = WorkCapabilityContract.create(ProjectScope.improve_existing(), WorkMode.REFACTOR, GenerationScope.BACKEND_ONLY)
    assert validate_work_capability(c) is c
    assert c.allows_surface("backend")
    assert not c.allows_surface("frontend")


def test_mode_project_constraint_is_enforced():
    with pytest.raises(ValueError, match="requires-existing-project"):
        WorkCapabilityContract.create(ProjectScope.create_new(), WorkMode.MIGRATE, GenerationScope.FULL_APPLICATION)


def test_existing_mutation_governance_is_preserved():
    c = WorkCapabilityContract.create(ProjectScope.improve_existing(), WorkMode.IMPROVE, GenerationScope.FRONTEND_ONLY)
    assert c.authorize((MutationIntent("frontend", "edit", "src/App.tsx"),))
    with pytest.raises(ScopeViolation):
        c.authorize((MutationIntent("backend", "edit", "api/app.py"),))


def test_invalid_contract_fails_closed():
    with pytest.raises(ValueError, match="invalid-work-capability"):
        validate_work_capability("bad")
