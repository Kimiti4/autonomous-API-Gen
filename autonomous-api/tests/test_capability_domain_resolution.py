import pytest
from app.engine.generation_scope import GenerationScope
from app.engine.project_scope import ProjectScope
from app.engine.work_capability import WorkCapabilityContract
from app.engine.work_mode import WorkMode
from app.engine.capability_domain_resolution import required_mutation_domain, validate_mutation_domains


@pytest.mark.parametrize("mode,domain", [
    (WorkMode.DOCUMENT, "documentation"),
    (WorkMode.TEST, "testing"),
    (WorkMode.ARCHITECTURE, "architecture"),
    (WorkMode.MIGRATE, "migration"),
    (WorkMode.REFACTOR, "refactor"),
])
def test_mode_resolves_required_domain(mode, domain):
    c = WorkCapabilityContract.create(ProjectScope.improve_existing(), mode, GenerationScope.FULL_APPLICATION)
    assert required_mutation_domain(c) == domain


def test_missing_required_domain_fails_closed():
    c = WorkCapabilityContract.create(ProjectScope.improve_existing(), WorkMode.DOCUMENT, GenerationScope.FULL_APPLICATION)
    with pytest.raises(ValueError, match="missing-required-mutation-domain"):
        validate_mutation_domains(c, ("frontend",))


def test_required_domain_is_accepted():
    c = WorkCapabilityContract.create(ProjectScope.improve_existing(), WorkMode.REFACTOR, GenerationScope.BACKEND_ONLY)
    validate_mutation_domains(c, ("refactor",))
