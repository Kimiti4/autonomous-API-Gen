from app.engine.api_ui_contracts import verify_api_ui_contract
from app.engine.backend_ir import BackendEndpoint, build_backend_ir
from app.engine.frontend_ir import FrontendProjectIR, FrontendScreen


def test_api_ui_contract_accepts_matching_route_and_authorization():
    backend = build_backend_ir(
        "ARCH-1",
        source_requirements=("R1",),
        endpoints=(BackendEndpoint(
            "EP1", "wallet", "/wallet", "GET",
            "WalletRequest", "WalletView", "wallet-read"
        ),),
    )
    frontend = FrontendProjectIR(
        "1", "ev-app",
        (FrontendScreen(
            "wallet", "/wallet", "Wallet", "WalletView",
            "wallet-read", ("refresh",)
        ),),
        "api-v1",
    )
    result = verify_api_ui_contract(backend, frontend)
    assert result.compatible, result.findings


def test_api_ui_contract_rejects_authorization_mismatch():
    backend = build_backend_ir(
        "ARCH-1", source_requirements=("R1",),
        endpoints=(BackendEndpoint(
            "EP1", "wallet", "/wallet", "GET",
            "WalletRequest", "WalletView", "wallet-read"
        ),),
    )
    frontend = FrontendProjectIR(
        "1", "ev-app",
        (FrontendScreen("wallet", "/wallet", "Wallet", "WalletView",
                        "admin-only", ("refresh",)),),
        "api-v1",
    )
    result = verify_api_ui_contract(backend, frontend)
    assert not result.compatible
    assert any("authorization" in x for x in result.findings)
