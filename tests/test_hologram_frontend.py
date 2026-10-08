from tiannara.application.compiler.composition import build_compiler_registry

def test_hologram_is_registered():
    assert "hologram" in {d.backend_id for d in build_compiler_registry().declarations()}

def test_hologram_has_distinct_runtime_model():
    from tiannara.domain.models.system_model import SystemModel, RequirementsReference
    model=SystemModel(system_name="Hologram Test",problem_statement="test",requirements_ref=RequirementsReference(graph_id="g",graph_hash="h"))
    result=build_compiler_registry().backend("hologram").generate(model)
    assert "lib/esap_app/page.ex" in result.files
    assert result.capability_manifest.metadata["runtime_model"]=="server_client_elixir"
