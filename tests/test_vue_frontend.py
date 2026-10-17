from tiannara.application.compiler.composition import build_compiler_registry

def test_vue_frontend_is_registered():
    ids={d.backend_id for d in build_compiler_registry().declarations()}
    assert "vue_ts" in ids

def test_vue_is_distinct_from_react():
    from tiannara.domain.models.system_model import SystemModel, RequirementsReference
    model=SystemModel(system_name="Vue Test",problem_statement="test",
      requirements_ref=RequirementsReference(graph_id="g",graph_hash="h"))
    b=build_compiler_registry().backend("vue_ts")
    result=b.generate(model)
    assert "src/App.vue" in result.files
    assert ".tsx" not in "\n".join(result.files)
    assert "react" not in "\n".join(result.files.values()).lower()


def test_vue_generation_has_real_build_config_and_behavioral_test():
    from tiannara.domain.models.system_model import SystemModel, RequirementsReference
    model = SystemModel(system_name='Vue "unsafe" <title>', problem_statement="test",
        requirements_ref=RequirementsReference(graph_id="g", graph_hash="h"))
    generated = build_compiler_registry().backend("vue_ts").generate(model)
    assert "vite.config.ts" in generated.files
    assert "@vitejs/plugin-vue" in generated.files["package.json"]
    assert "mount(App)" in generated.files["src/App.test.ts"]
    assert "expect(true).toBe(true)" not in generated.files["src/App.test.ts"]
    assert "const title = \"Vue \\\"unsafe\\\" <title>\"" in generated.files["src/App.vue"]
    assert "<h1>{{ title }}</h1>" in generated.files["src/App.vue"]
    profile = build_compiler_registry().backend("vue_ts").build_profile(model.system_name)
    assert profile.test_command == ["npm", "test"]
