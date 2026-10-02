from app.engine.frontend_certification import certify_frontend_compiler
from app.engine.frontend_ir import FrontendProjectIR, FrontendScreen
from app.engine.frontend_registry import FrontendCompilerRegistry, FrontendTarget
from app.engine.react_typescript_compiler import ReactTypeScriptCompiler


def test_frontend_certification_rejects_missing_semantics():
    ir = FrontendProjectIR(
        "1", "ev-app",
        (FrontendScreen(
            "wallet", "/wallet", "Wallet", "WalletView", "wallet-read",
            ("send",), ("screen-reader",)
        ),),
        "api-v1", ("responsive",), ("API_BASE_URL",),
    )
    compiler = ReactTypeScriptCompiler()
    result = certify_frontend_compiler(
        ir, compiler.compile(ir)
    )
    assert not result.certified
    assert result.findings


def test_registry_still_rejects_invalid_frontend_ir():
    registry = FrontendCompilerRegistry()
    compiler = ReactTypeScriptCompiler()
    registry.register(
        FrontendTarget("web-react-typescript", "web", "typescript", "react"),
        compiler,
    )
    ir = FrontendProjectIR("", "", (), "")
    result = registry.compile("web-react-typescript", ir)
    assert result.diagnostics
