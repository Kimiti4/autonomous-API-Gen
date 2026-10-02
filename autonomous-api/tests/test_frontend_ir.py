from app.engine.frontend_ir import FrontendProjectIR, FrontendScreen, validate_frontend_ir
from app.engine.frontend_contracts import frontend_contract_manifest


def test_frontend_ir_is_platform_neutral():
    ir = FrontendProjectIR(
        "1", "ev-app",
        (FrontendScreen(
            "wallet", "/wallet", "Wallet",
            "WalletView", "wallet-read",
            ("send", "refresh"), ("keyboard-navigation", "screen-reader")
        ),),
        "api-v1",
        ("responsive",),
        ("API_BASE_URL",),
    )
    assert validate_frontend_ir(ir) == ()
    manifest = frontend_contract_manifest(ir)
    assert manifest["screens"][0]["data_contract"] == "WalletView"
    assert manifest["screens"][0]["authorization_policy"] == "wallet-read"
    assert "screen-reader" in manifest["screens"][0]["accessibility_requirements"]


def test_invalid_frontend_ir_fails_closed():
    ir = FrontendProjectIR("", "", (FrontendScreen("x", "wallet", ""),), "")
    assert validate_frontend_ir(ir)
