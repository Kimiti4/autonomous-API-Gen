from app.engine.backend_ir import BackendEndpoint, build_backend_ir
from app.engine.express_compiler import ExpressBackendCompiler


def test_express_compiler_generates_equivalent_backend_layers():
    ir = build_backend_ir(
        "ARCH-1",
        source_requirements=("R1",),
        endpoints=(BackendEndpoint("EP1", "create_transfer", "/transfers", "POST"),),
    )
    before = ir.to_dict()
    result = ExpressBackendCompiler().compile(ir)
    assert result.diagnostics == ()
    paths = {a.path for a in result.artifacts}
    assert {"app.js", "service.js", "repository.js", "server.js",
            "package.json", "contracts/errors.json"} <= paths
    app = next(a.content for a in result.artifacts if a.path == "app.js")
    assert "router.post" in app and "/transfers" in app
    assert ir.to_dict() == before


def test_express_compiler_fails_closed():
    ir = build_backend_ir("ARCH-1", source_requirements=("R1",), error_contract="")
    result = ExpressBackendCompiler().compile(ir)
    assert result.artifacts == ()
    assert result.diagnostics
