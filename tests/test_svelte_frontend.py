from tiannara.application.compiler.composition import build_compiler_registry

def test_svelte_frontend_is_registered():
    assert "svelte_ts" in {d.backend_id for d in build_compiler_registry().declarations()}

def test_svelte_emits_svelte_specific_structure():
    from tiannara.domain.models.system_model import SystemModel, RequirementsReference
    model=SystemModel(system_name="Svelte Test",problem_statement="test",requirements_ref=RequirementsReference(graph_id="g",graph_hash="h"))
    result=build_compiler_registry().backend("svelte_ts").generate(model)
    assert "src/App.svelte" in result.files and "svelte.config.js" in result.files
    assert '<div id="app"></div><script type="module" src="/src/main.ts"></script>' in result.files["index.html"]


def test_svelte_uses_svelte5_mount_and_real_component_test():
    import json
    from tiannara.domain.models.system_model import SystemModel, RequirementsReference
    model=SystemModel(system_name='Svelte "unsafe" <title>',problem_statement="test",requirements_ref=RequirementsReference(graph_id="g",graph_hash="h"))
    backend=build_compiler_registry().backend("svelte_ts")
    result=backend.generate(model)
    assert f"const title = {json.dumps(model.system_name, ensure_ascii=True)};" in result.files["src/App.svelte"]
    assert "mount(App, { target: document.body })" in result.files["src/main.ts"]
    assert "render(App)" in result.files["src/App.test.ts"]
    vite_config = result.files["vite.config.ts"]
    assert 'environment: "jsdom"' in vite_config
    assert 'url: "http://localhost/"' in vite_config
    assert "expect(true).toBe(true)" not in result.files["src/App.test.ts"]
    assert "src/App.test.ts" in backend.build_profile(model.system_name).required_files
    assert "index.html" in backend.build_profile(model.system_name).required_files
