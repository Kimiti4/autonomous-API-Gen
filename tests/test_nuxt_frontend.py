from tiannara.application.compiler.composition import build_compiler_registry

def test_nuxt_frontend_is_registered():
    assert "nuxt_ts" in {d.backend_id for d in build_compiler_registry().declarations()}

def test_nuxt_emits_nuxt_specific_structure():
    from tiannara.domain.models.system_model import SystemModel, RequirementsReference
    model=SystemModel(system_name="Nuxt Test",problem_statement="test",requirements_ref=RequirementsReference(graph_id="g",graph_hash="h"))
    result=build_compiler_registry().backend("nuxt_ts").generate(model)
    assert "nuxt.config.ts" in result.files and "app/app.vue" in result.files


def test_nuxt4_uses_conventional_app_directory_and_real_component_test():
    import json
    from tiannara.domain.models.system_model import SystemModel, RequirementsReference
    model=SystemModel(system_name='Nuxt "unsafe" <title>',problem_statement="test",requirements_ref=RequirementsReference(graph_id="g",graph_hash="h"))
    backend=build_compiler_registry().backend("nuxt_ts")
    result=backend.generate(model)
    assert f"const title = {json.dumps(model.system_name, ensure_ascii=True)}" in result.files["app/app.vue"]
    assert "mount(App)" in result.files["tests/app.test.ts"]
    assert "vitest.config.ts" in result.files
    assert "expect(true).toBe(true)" not in result.files["tests/app.test.ts"]
