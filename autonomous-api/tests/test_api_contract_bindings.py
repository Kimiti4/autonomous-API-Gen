from app.engine.api_contract_bindings import verify_api_contract_bindings
from app.engine.api_ir import ApiContractIR, ApiOperation
from app.engine.backend_ir import BackendEndpoint, build_backend_ir
from app.engine.frontend_ir import FrontendProjectIR, FrontendScreen


def test_canonical_api_binds_backend_and_frontend():
    api = ApiContractIR("1", "wallet-api", (
        ApiOperation("wallet", "GET", "/wallet", None, "WalletView", "wallet-read"),
    ), "stable errors")
    backend = build_backend_ir("A1", source_requirements=("R1",), endpoints=(
        BackendEndpoint("E1", "wallet", "/wallet", "GET", None, "WalletView", "wallet-read"),
    ))
    frontend = FrontendProjectIR("1", "app", (
        FrontendScreen("wallet", "/wallet", "Wallet", "WalletView", "wallet-read", ("refresh",)),
    ), "v1")
    assert verify_api_contract_bindings(api, backend, frontend) == ()


def test_binding_rejects_backend_schema_drift():
    api = ApiContractIR("1", "wallet-api", (
        ApiOperation("wallet", "GET", "/wallet", None, "WalletView", "wallet-read"),
    ), "stable errors")
    backend = build_backend_ir("A1", source_requirements=("R1",), endpoints=(
        BackendEndpoint("E1", "wallet", "/wallet", "GET", None, "WrongView", "wallet-read"),
    ))
    frontend = FrontendProjectIR("1", "app", (
        FrontendScreen("wallet", "/wallet", "Wallet", "WalletView", "wallet-read", ("refresh",)),
    ), "v1")
    findings = verify_api_contract_bindings(api, backend, frontend)
    assert any("response schema mismatch" in x for x in findings)
