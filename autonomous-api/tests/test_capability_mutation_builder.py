from app.engine.capability_domain_resolution import build_capability_mutation
from app.engine.generation_scope import GenerationScope
from app.engine.project_scope import ProjectScope
from app.engine.work_capability import WorkCapabilityContract
from app.engine.work_mode import WorkMode

def test_builds_mode_required_mutation_with_explicit_evidence():
    c=WorkCapabilityContract.create(ProjectScope.improve_existing(),WorkMode.DOCUMENT,GenerationScope.FULL_APPLICATION)
    spec=build_capability_mutation(c,"doc-1",("README.md",),"update docs",("verified-source",),lambda g:g)
    assert spec.mutation.domain=="documentation"
    assert spec.verification_properties

def test_builds_cross_stack_mutation():
    c=WorkCapabilityContract.create(ProjectScope.improve_existing(),WorkMode.CROSS_STACK,GenerationScope.FULL_APPLICATION)
    spec=build_capability_mutation(c,"x-1",("src",),"cross stack",("e",),lambda g:g)
    assert spec.mutation.domain=="crossstack"
