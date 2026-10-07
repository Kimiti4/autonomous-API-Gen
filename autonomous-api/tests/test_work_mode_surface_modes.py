from app.engine.project_scope import ProjectScope
from app.engine.generation_scope import GenerationScope
from app.engine.work_capability import WorkCapabilityContract
from app.engine.work_mode import WorkMode, WorkModeContract


def test_surface_only_modes_are_bounded_for_new_and_existing_projects():
    cases = [
        (WorkMode.FRONTEND_ONLY, "frontend", ProjectScope.create_new()),
        (WorkMode.FRONTEND_ONLY, "frontend", ProjectScope.improve_existing()),
        (WorkMode.BACKEND_ONLY, "backend", ProjectScope.create_new()),
        (WorkMode.BACKEND_ONLY, "backend", ProjectScope.maintain_existing()),
        (WorkMode.API_CONTRACT_ONLY, "api_contract", ProjectScope.create_new()),
        (WorkMode.API_CONTRACT_ONLY, "api_contract", ProjectScope.improve_existing()),
    ]
    scopes = {
        "frontend": GenerationScope.FRONTEND_ONLY,
        "backend": GenerationScope.BACKEND_ONLY,
        "api_contract": GenerationScope.API_CONTRACT_ONLY,
    }
    for mode, allowed_surface, project in cases:
        contract = WorkCapabilityContract.create(project, mode, scopes[allowed_surface])
        assert contract.allows_surface(allowed_surface)
        for surface in {"frontend", "backend", "api_contract"} - {allowed_surface}:
            assert not contract.allows_surface(surface)


def test_surface_only_modes_do_not_require_existing_projects():
    for mode in (
        WorkMode.FRONTEND_ONLY,
        WorkMode.BACKEND_ONLY,
        WorkMode.API_CONTRACT_ONLY,
    ):
        assert not WorkModeContract.for_mode(mode).requires_existing_project


def test_invalid_surface_remains_fail_closed():
    contract = WorkModeContract.for_mode(WorkMode.FRONTEND_ONLY)
    try:
        contract.allows_surface("database")
    except ValueError as exc:
        assert str(exc) == "unknown-software-surface:database"
    else:
        raise AssertionError("unknown surface must fail closed")
