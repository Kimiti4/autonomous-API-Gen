from tiannara.application.compiler.composition import build_compiler_registry

def test_liveview_frontend_is_registered():
    assert "phoenix_liveview" in {d.backend_id for d in build_compiler_registry().declarations()}

def test_liveview_uses_server_reactive_model():
    from tiannara.domain.models.system_model import SystemModel, RequirementsReference
    model=SystemModel(system_name="LiveView Test",problem_statement="test",requirements_ref=RequirementsReference(graph_id="g",graph_hash="h"))
    result=build_compiler_registry().backend("phoenix_liveview").generate(model)
    assert "lib/esap_app_web/live/page_live.ex" in result.files
    assert "use Phoenix.LiveView" in result.files["lib/esap_app_web/live/page_live.ex"]
