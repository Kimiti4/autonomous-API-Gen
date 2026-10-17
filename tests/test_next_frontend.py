from tiannara.application.compiler.composition import build_compiler_registry

def test_next_frontend_is_registered():
    assert "next_ts" in {d.backend_id for d in build_compiler_registry().declarations()}

def test_next_emits_next_specific_structure():
    from tiannara.domain.models.system_model import SystemModel, RequirementsReference
    model=SystemModel(system_name="Next Test",problem_statement="test",requirements_ref=RequirementsReference(graph_id="g",graph_hash="h"))
    result=build_compiler_registry().backend("next_ts").generate(model)
    assert "app/page.tsx" in result.files and "app/layout.tsx" in result.files
    assert result.files["app/layout.tsx"].endswith("</html>}")
    assert "</html}" not in result.files["app/layout.tsx"]


def test_next_generation_uses_safe_title_and_real_render_test():
    import json
    from tiannara.domain.models.system_model import SystemModel, RequirementsReference
    model=SystemModel(system_name='Next "unsafe" <title>',problem_statement="test",requirements_ref=RequirementsReference(graph_id="g",graph_hash="h"))
    backend=build_compiler_registry().backend("next_ts")
    result=backend.generate(model)
    assert f"const title = {json.dumps(model.system_name, ensure_ascii=True)};" in result.files["app/page.tsx"]
    assert "renderToStaticMarkup(<Page />)" in result.files["app/page.test.tsx"]
    assert "expect(true).toBe(true)" not in result.files["app/page.test.tsx"]
    assert "vite.config.ts" in result.files
    assert backend.build_profile(model.system_name).test_command == ["npm", "test"]
