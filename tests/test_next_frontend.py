from tiannara.application.compiler.composition import build_compiler_registry

def test_next_frontend_is_registered():
    assert "next_ts" in {d.backend_id for d in build_compiler_registry().declarations()}

def test_next_emits_next_specific_structure():
    from tiannara.domain.models.system_model import SystemModel, RequirementsReference
    model=SystemModel(system_name="Next Test",problem_statement="test",requirements_ref=RequirementsReference(graph_id="g",graph_hash="h"))
    result=build_compiler_registry().backend("next_ts").generate(model)
    assert "app/page.tsx" in result.files and "app/layout.tsx" in result.files
