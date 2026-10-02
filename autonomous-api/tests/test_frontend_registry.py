from app.engine.frontend_ir import FrontendProjectIR, FrontendScreen
from app.engine.frontend_registry import FrontendCompilerRegistry, FrontendTarget
from app.engine.react_typescript_compiler import ReactTypeScriptCompiler


def test_web_target_is_registered_and_compiles():
    ir = FrontendProjectIR(
        "1", "ev-app",
        (FrontendScreen("wallet", "/wallet", "Wallet", "WalletView",
                        "wallet-read", ("send",), ("screen-reader",)),),
        "api-v1",
    )
    registry = FrontendCompilerRegistry()
    compiler = ReactTypeScriptCompiler()
    registry.register(
        FrontendTarget("web-react-typescript", "web", "typescript", "react"),
        compiler,
    )
    result = registry.compile("web-react-typescript", ir)
    assert result.diagnostics == ()
    assert result.source_schema_version == "1"
    assert any(a.path == "src/App.tsx" for a in result.artifacts)
