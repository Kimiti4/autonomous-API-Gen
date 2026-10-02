from app.engine.api_ir import ApiContractIR, ApiError, ApiOperation
from app.engine.openapi_projection import to_openapi


def test_openapi_projection_preserves_api_semantics():
    ir = ApiContractIR(
        "1", "wallet-api",
        (ApiOperation(
            "transfer", "POST", "/wallet/transfers",
            "TransferRequest", "TransferResponse", "wallet-transfer",
            (ApiError("INSUFFICIENT_FUNDS", 409, False),), True, False, "v1"
        ),),
        "stable machine-readable errors", "bearer",
    )
    doc = to_openapi(ir)
    op = doc["paths"]["/wallet/transfers"]["post"]
    assert op["operationId"] == "transfer"
    assert op["x-request-schema"] == "TransferRequest"
    assert op["x-response-schema"] == "TransferResponse"
    assert op["x-authorization-policy"] == "wallet-transfer"
    assert op["x-idempotency-required"] is True
    assert op["409"]["x-error-code"] == "INSUFFICIENT_FUNDS"
    assert doc["components"]["securitySchemes"]["default"]["scheme"] == "bearer"
