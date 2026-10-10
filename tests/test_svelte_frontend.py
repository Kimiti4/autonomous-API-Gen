from tiannara.application.compiler.composition import build_compiler_registry

def test_svelte_frontend_is_registered():
    assert "svelte_ts" in {d.backend_id for d in build_compiler_registry().declarations()}

def test_svelte_emits_svelte_specific_structure():
    from tiannara.domain.models.system_model import SystemModel, RequirementsReference
    model=SystemModel(system_name="Svelte Test",problem_statement="test",requirements_ref=RequirementsReference(graph_id="g",graph_hash="h"))
    result=build_compiler_registry().backend("svelte_ts").generate(model)
    assert "src/App.svelte" in result.files and "svelte.config.js" in result.files
