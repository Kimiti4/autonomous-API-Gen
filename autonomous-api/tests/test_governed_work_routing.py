import pytest
from app.engine.governed_work_routing import WorkMode, route_work
from app.engine.generation_scope import GenerationScope

def test_create_routes_only_to_new_project():
    r=route_work(mode=WorkMode.CREATE,scope=GenerationScope.FULL_APPLICATION,existing_project=False)
    assert r.project.intent.value=="create"

def test_maintain_existing_routes():
    r=route_work(mode=WorkMode.MAINTAIN,scope=GenerationScope.BACKEND_ONLY,existing_project=True)
    assert r.project.intent.value=="maintain"
    assert r.generation.allows("backend")

def test_improve_frontend_only_preserves_backend_and_api():
    r=route_work(mode=WorkMode.IMPROVE,scope=GenerationScope.FRONTEND_ONLY,existing_project=True)
    assert r.generation.allows("frontend")
    assert not r.generation.allows("backend")
    assert not r.generation.allows("api_contract")

def test_create_existing_project_fails_closed():
    with pytest.raises(ValueError,match="work-mode-existing-project-mismatch"):
        route_work(mode=WorkMode.CREATE,scope=GenerationScope.FULL_APPLICATION,existing_project=True)

def test_maintain_new_project_fails_closed():
    with pytest.raises(ValueError,match="work-mode-existing-project-mismatch"):
        route_work(mode=WorkMode.MAINTAIN,scope=GenerationScope.FULL_APPLICATION,existing_project=False)
