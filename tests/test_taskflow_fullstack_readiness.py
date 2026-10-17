from tiannara.application.compiler.derivation import derive_compilation_requirements
from tiannara.domain.models.system_model import SystemModel


def test_taskflow_readiness_requires_explicit_full_stack_artifact_families():
    # The current derivation is intentionally backend-only. This test makes
    # that limitation visible instead of allowing a backend-only plan to be
    # mistaken for a certified full-stack application: readiness must NOT
    # claim full-stack artifact families until the derivation emits them.
    model = SystemModel.model_validate({
        "system_name": "TaskFlow",
        "requirements_ref": {"graph_id": "TASKFLOW-GOLDEN-001", "graph_hash": "pending"},
        "services": [{
            "id": "taskflow",
            "name": "taskflow",
            "domain_id": "taskflow",
            "responsibilities": ["manage workspaces, projects and tasks"],
        }],
        "data_models": [],
    })
    requirements = derive_compilation_requirements(model)
    kinds = {r.artifact_kind.value for r in requirements}
    # Backend-only today: full-stack families are not yet derived.
    assert kinds == {"backend_service"}
