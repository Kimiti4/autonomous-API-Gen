from tiannara.application.compiler.derivation import derive_compilation_requirements
from tiannara.domain.models.system_model import SystemModel


def test_taskflow_readiness_requires_explicit_full_stack_artifact_families():
    # The current derivation is intentionally backend-only. This test makes
    # that limitation visible instead of allowing a backend-only plan to be
    # mistaken for a certified full-stack application.
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
    assert {"backend_service", "frontend_application", "database_migration", "infrastructure_provision", "deployment", "documentation"}.issubset(kinds)
