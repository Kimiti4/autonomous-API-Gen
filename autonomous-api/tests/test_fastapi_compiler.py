from app.engine.backend_ir import BackendEndpoint, build_backend_ir
from app.engine.fastapi_compiler import FastAPIBackendCompiler


def test_fastapi_target_generates_real_project_artifacts():
    ir = build_backend_ir(
        "ARCH-1",
        source_requirements=("R1",),
        endpoints=(BackendEndpoint("EP1", "create_transfer", "/transfers", "POST"),),
        configuration_keys=("SERVICE_NAME",),
    )
    result = FastAPIBackendCompiler().compile(ir)
    assert result.diagnostics == ()
    paths = {a.path for a in result.artifacts}
    assert {"app/main.py", "app/settings.py", "requirements.txt",
            "contracts/errors.json", "tests/test_health.py"} <= paths
    main = next(a.content for a in result.artifacts if a.path == "app/main.py")
    assert '@router.post("/transfers")' in main
    assert "create_transfer" in main


def test_fastapi_compiler_fails_closed():
    ir = build_backend_ir("ARCH-1", source_requirements=("R1",), error_contract="")
    result = FastAPIBackendCompiler().compile(ir)
    assert result.artifacts == ()
    assert result.diagnostics
