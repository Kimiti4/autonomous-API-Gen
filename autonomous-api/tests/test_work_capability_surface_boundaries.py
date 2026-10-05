from app.engine.generation_scope import GenerationScope
from app.engine.project_scope import ProjectScope
from app.engine.work_capability import WorkCapabilityContract
from app.engine.work_mode import WorkMode


def test_surface_mode_cannot_be_widened_by_full_generation_scope():
    project = ProjectScope.maintain_existing()
    contract = WorkCapabilityContract.create(project, WorkMode.FRONTEND_ONLY, GenerationScope.FULL_APPLICATION)
    assert contract.allows_surface("frontend")
    assert not contract.allows_surface("backend")
    assert not contract.allows_surface("api_contract")
