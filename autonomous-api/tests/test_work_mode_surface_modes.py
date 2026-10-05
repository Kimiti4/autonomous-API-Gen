from app.engine.work_mode import WorkMode, WorkModeContract


def test_surface_only_modes_exist_and_are_bounded():
    assert WorkModeContract.for_mode(WorkMode.FRONTEND_ONLY).allows_surface("frontend")
    assert not WorkModeContract.for_mode(WorkMode.FRONTEND_ONLY).allows_surface("backend")
    assert WorkModeContract.for_mode(WorkMode.BACKEND_ONLY).allows_surface("backend")
    assert not WorkModeContract.for_mode(WorkMode.BACKEND_ONLY).allows_surface("frontend")
    assert WorkModeContract.for_mode(WorkMode.API_CONTRACT_ONLY).allows_surface("api_contract")
    assert not WorkModeContract.for_mode(WorkMode.API_CONTRACT_ONLY).allows_surface("backend")


def test_surface_only_modes_require_existing_projects():
    for mode in (
        WorkMode.FRONTEND_ONLY,
        WorkMode.BACKEND_ONLY,
        WorkMode.API_CONTRACT_ONLY,
    ):
        assert WorkModeContract.for_mode(mode).requires_existing_project
