import pytest
from app.engine.generation_scope import GenerationScope
from app.engine.project_scope import ProjectScope
from app.engine.work_capability import WorkCapabilityContract
from app.engine.work_mode import WorkMode
from app.engine.work_mode_scope_validation import validate_mode_surface


@pytest.mark.parametrize("mode,scope", [
    (WorkMode.SEO, GenerationScope.BACKEND_ONLY),
    (WorkMode.CROSS_STACK, GenerationScope.FRONTEND_ONLY),
])
def test_incompatible_mode_surface_fails_closed(mode, scope):
    c = WorkCapabilityContract.create(ProjectScope.improve_existing(), mode, scope)
    with pytest.raises(ValueError, match="incompatible-work-mode-and-generation-scope"):
        validate_mode_surface(c)


@pytest.mark.parametrize("mode,scope", [
    (WorkMode.SEO, GenerationScope.FRONTEND_ONLY),
    (WorkMode.DOCUMENT, GenerationScope.API_CONTRACT_ONLY),
    (WorkMode.TEST, GenerationScope.BACKEND_ONLY),
    (WorkMode.REFACTOR, GenerationScope.FULL_APPLICATION),
])
def test_valid_mode_surface_combinations_are_accepted(mode, scope):
    c = WorkCapabilityContract.create(ProjectScope.improve_existing(), mode, scope)
    validate_mode_surface(c)
