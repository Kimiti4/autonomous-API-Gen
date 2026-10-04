import pytest
from app.engine.capability_contract import WorkCapabilityContract
from app.engine.generation_scope import GenerationScope
from app.engine.project_scope import ProjectScope
from app.engine.scope_authorization import MutationIntent, ScopeViolation
from app.engine.work_mode import WorkMode
from app.engine.governed_evolution_transaction import execute_governed_evolution_transaction


def test_governed_entry_point_rejects_unauthorized_surface():
    capability = WorkCapabilityContract.create(
        ProjectScope.improve_existing(), WorkMode.IMPROVE, GenerationScope.FRONTEND_ONLY
    )
    with pytest.raises(ScopeViolation):
        capability.authorize((MutationIntent("backend", "edit", "api/app.py"),))


def test_governed_entry_point_is_capability_aware():
    capability = WorkCapabilityContract.create(
        ProjectScope.improve_existing(), WorkMode.IMPROVE, GenerationScope.BACKEND_ONLY
    )
    assert capability.allows_surface("backend")
    assert not capability.allows_surface("frontend")


def test_governed_entry_point_requires_valid_capability():
    with pytest.raises(ValueError, match="invalid-work-capability"):
        from app.engine.capability_contract import validate_work_capability
        validate_work_capability("invalid")
