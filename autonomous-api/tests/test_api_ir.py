from app.engine.api_ir import ApiContractIR, ApiError, ApiOperation, validate_api_contract


def test_api_contract_models_errors_idempotency_pagination_and_versioning():
    ir = ApiContractIR(
        "1", "wallet-api",
        (ApiOperation(
            "transfer", "POST", "/wallet/transfers",
            "TransferRequest", "TransferResponse", "wallet-transfer",
            (ApiError("INSUFFICIENT_FUNDS", 409),), True, False, "v1"
        ), ApiOperation(
            "list_wallets", "GET", "/wallets",
            None, "WalletList", "wallet-read", (), False, True, "v1"
        )),
        "stable machine-readable errors", "bearer",
    )
    assert validate_api_contract(ir) == ()


def test_api_contract_fails_invalid_semantics():
    ir = ApiContractIR("1", "bad", (
        ApiOperation("x", "GET", "relative", paginated=True, version="v1"),
    ), "")
    findings = validate_api_contract(ir)
    assert findings
