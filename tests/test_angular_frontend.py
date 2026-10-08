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
