from app.engine.backend_ir import BackendEndpoint, build_backend_ir
from app.engine.layered_fastapi_compiler import LayeredFastAPICompiler


def test_layered_compiler_generates_separate_boundaries():
    ir = build_backend_ir(
        "ARCH-1",
        source_requirements=("R1",),
        endpoints=(BackendEndpoint("EP1", "create_transfer", "/transfers", "POST"),),
    )
    result = LayeredFastAPICompiler().compile(ir)
    assert result.diagnostics == ()
    paths = {a.path for a in result.artifacts}
    assert {"app/schemas.py", "app/repository.py", "app/service.py"} <= paths
    service = next(a.content for a in result.artifacts if a.path == "app/service.py")
    assert "self.repository.create_transfer" in service


def test_layered_compiler_does_not_mutate_ir():
    ir = build_backend_ir("ARCH-1", source_requirements=("R1",))
    before = ir.to_dict()
    LayeredFastAPICompiler().compile(ir)
    assert ir.to_dict() == before
