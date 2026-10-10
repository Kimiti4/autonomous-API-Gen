from tiannara.application.compiler.composition import build_compiler_registry

def test_scenic_is_registered():
    assert "scenic" in {d.backend_id for d in build_compiler_registry().declarations()}

def test_scenic_has_native_gui_runtime_model():
    from tiannara.domain.models.system_model import SystemModel, RequirementsReference
    model=SystemModel(system_name="Scenic Test",problem_statement="test",requirements_ref=RequirementsReference(graph_id="g",graph_hash="h"))
    result=build_compiler_registry().backend("scenic").generate(model)
    assert "lib/esap_app/scene.ex" in result.files
    assert result.capability_manifest.metadata["runtime_model"]=="native_gui"
