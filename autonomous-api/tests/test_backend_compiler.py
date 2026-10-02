from app.engine.backend_compiler import TemplateBackendCompiler, compile_backend
from app.engine.backend_ir import build_backend_ir


def test_compiler_consumes_backend_ir_without_changing_source():
    ir = build_backend_ir("ARCH-1", source_requirements=("R1",),
                          configuration_keys=("SERVICE_NAME",))
    before = ir.to_dict()
    result = compile_backend(ir, TemplateBackendCompiler("python-reference", ".py"))
    assert result.diagnostics == ()
    assert result.source_schema_version == "CAP-003-BackendIR.v1"
    assert any(a.path.startswith("src/") for a in result.artifacts)
    assert ir.to_dict() == before


def test_invalid_backend_ir_fails_closed():
    ir = build_backend_ir("ARCH-1", source_requirements=("R1",), error_contract="")
    result = compile_backend(ir, TemplateBackendCompiler("python-reference", ".py"))
    assert result.artifacts == ()
    assert result.diagnostics
