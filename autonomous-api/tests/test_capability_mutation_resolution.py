import pytest
from app.engine.capability_domain_resolution import required_mutation_domain, resolve_mutation_factory
from app.engine.generation_scope import GenerationScope
from app.engine.project_scope import ProjectScope
from app.engine.work_capability import WorkCapabilityContract
from app.engine.work_mode import WorkMode

@pytest.mark.parametrize("mode,domain", [
(WorkMode.GENERATE,"generate"),(WorkMode.MAINTAIN,"maintain"),(WorkMode.IMPROVE,"improve"),
(WorkMode.DOCUMENT,"documentation"),(WorkMode.SEO,"seo"),(WorkMode.TEST,"testing"),
(WorkMode.ARCHITECTURE,"architecture"),(WorkMode.MIGRATE,"migration"),
(WorkMode.REFACTOR,"refactor"),(WorkMode.CROSS_STACK,"crossstack")])
def test_every_bucket_two_mode_resolves_factory(mode,domain):
    c=WorkCapabilityContract.create(ProjectScope.improve_existing(),mode,GenerationScope.FULL_APPLICATION)
    assert required_mutation_domain(c)==domain
    assert callable(resolve_mutation_factory(c))

def test_new_project_generation_resolves_factory():
    c=WorkCapabilityContract.create(ProjectScope.create_new(),WorkMode.GENERATE,GenerationScope.FULL_APPLICATION)
    assert callable(resolve_mutation_factory(c))
