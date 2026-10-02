from app.engine.frontend_certification import certify_frontend_compiler
from app.engine.frontend_ir import FrontendProjectIR, FrontendScreen
from app.engine.react_typescript_compiler import ReactTypeScriptCompiler


def test_react_target_preserves_frontend_semantics():
    ir = FrontendProjectIR(
        "1", "ev-app",
        (FrontendScreen(
            "wallet", "/wallet", "Wallet", "WalletView", "wallet-read",
            ("send", "refresh"), ("screen-reader", "keyboard-navigation")
        ),),
        "api-v1", ("responsive",), ("API_BASE_URL",),
    )
    result = ReactTypeScriptCompiler().compile(ir)
    certification = certify_frontend_compiler(ir, result)
    assert certification.certified, certification.findings
