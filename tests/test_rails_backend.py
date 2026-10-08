from tiannara.application.compiler.composition import build_compiler_registry

def test_rails_backend_is_registered():
    ids={d.backend_id for d in build_compiler_registry().declarations()}
    assert "rails" in ids

def test_rails_is_independent():
    from tiannara.domain.models.system_model import SystemModel, RequirementsReference
    model=SystemModel(system_name="Rails Test",problem_statement="test",
      requirements_ref=RequirementsReference(graph_id="g",graph_hash="h"))
    b=build_compiler_registry().backend("rails")
    result=b.generate(model)
    assert "Gemfile" in result.files
    assert "config/routes.rb" in result.files
    assert "nestjs" not in "\n".join(result.files.values()).lower()
