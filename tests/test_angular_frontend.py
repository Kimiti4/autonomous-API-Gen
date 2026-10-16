from tiannara.application.compiler.composition import build_compiler_registry

def test_angular_frontend_is_registered():
    ids={d.backend_id for d in build_compiler_registry().declarations()}
    assert "angular_ts" in ids

def test_angular_is_not_react_or_vue_output():
    from tiannara.domain.models.system_model import SystemModel, RequirementsReference
    model=SystemModel(system_name="Angular Test",problem_statement="test",
      requirements_ref=RequirementsReference(graph_id="g",graph_hash="h"))
    result=build_compiler_registry().backend("angular_ts").generate(model)
    assert "src/app/app.component.ts" in result.files
    assert "angular.json" in result.files
    source="\n".join(result.files.values()).lower()
    assert "react" not in source and "vue" not in source


def test_angular_uses_safe_title_and_behavioral_vitest_test():
    import json
    from tiannara.domain.models.system_model import SystemModel, RequirementsReference
    model=SystemModel(system_name='Angular "unsafe" <title>',problem_statement="test",requirements_ref=RequirementsReference(graph_id="g",graph_hash="h"))
    backend=build_compiler_registry().backend("angular_ts")
    result=backend.generate(model)
    assert f"readonly title = {json.dumps(model.system_name, ensure_ascii=True)};" in result.files["src/app/app.component.ts"]
    assert "@angular/build:unit-test" in result.files["angular.json"]
    assert "src/index.html" in result.files
    assert "tsconfig.spec.json" in result.files
    assert "index":"src/index.html" in result.files["angular.json"]
    assert 'from "vitest"' in result.files["src/app/app.component.spec.ts"]
    assert 'querySelector("h1")' in result.files["src/app/app.component.spec.ts"]
    assert "toBeTruthy" not in result.files["src/app/app.component.spec.ts"]
    assert backend.build_profile(model.system_name).test_command == ["npm", "test"]
