from tiannara.application.compiler.composition import build_compiler_registry

def test_express_backend_is_registered():
    ids={d.backend_id for d in build_compiler_registry().declarations()}
    assert "express" in ids
    d=next(x for x in build_compiler_registry().declarations() if x.backend_id=="express")
    assert d.metadata["runtime"]=="node.js"

def test_express_is_distinct_from_nestjs():
    from tiannara.domain.models.system_model import SystemModel, RequirementsReference
    model=SystemModel(system_name="Express Test",problem_statement="test",
      requirements_ref=RequirementsReference(graph_id="g",graph_hash="h"))
    b=build_compiler_registry().backend("express")
    result=b.generate(model)
    assert "src/index.ts" in result.files
    assert "@nestjs" not in "\n".join(result.files.values())
