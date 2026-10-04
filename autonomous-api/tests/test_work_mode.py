import pytest
from app.engine.work_mode import WorkMode, WorkModeContract


@pytest.mark.parametrize("mode", list(WorkMode))
def test_all_bucket_two_work_modes_are_explicit(mode):
    contract = WorkModeContract.for_mode(mode)
    assert contract.mode is mode


@pytest.mark.parametrize(
    "mode",
    [WorkMode.MAINTAIN, WorkMode.IMPROVE, WorkMode.DOCUMENT, WorkMode.SEO,
     WorkMode.TEST, WorkMode.MIGRATE, WorkMode.REFACTOR],
)
def test_existing_project_modes_fail_closed_on_new_projects(mode):
    with pytest.raises(ValueError, match="requires-existing-project"):
        WorkModeContract.for_mode(mode).validate_project_kind("new_project")


@pytest.mark.parametrize("mode", [WorkMode.GENERATE, WorkMode.ARCHITECTURE, WorkMode.CROSS_STACK])
def test_new_project_capable_modes_accept_new_projects(mode):
    WorkModeContract.for_mode(mode).validate_project_kind("new_project")


def test_invalid_mode_and_project_kind_fail_closed():
    with pytest.raises(ValueError, match="invalid-work-mode"):
        WorkModeContract.for_mode("unknown")
    with pytest.raises(ValueError, match="invalid-project-kind"):
        WorkModeContract.for_mode(WorkMode.GENERATE).validate_project_kind("other")
