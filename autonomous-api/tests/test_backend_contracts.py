from app.engine.backend_contracts import contract_manifest, endpoint_contracts
from app.engine.backend_ir import BackendEndpoint, build_backend_ir


def test_contract_manifest_preserves_language_neutral_semantics():
    ir = build_backend_ir(
        "ARCH-1", source_requirements=("R1",),
        endpoints=(BackendEndpoint(
            "EP1", "create_transfer", "/transfers", "POST",
            "TransferRequest", "TransferResponse", "transfer-write"
        ),),
        configuration_keys=("SERVICE_NAME",),
    )
    manifest = contract_manifest(ir)
    assert manifest["operations"][0]["request_schema"] == "TransferRequest"
    assert manifest["operations"][0]["authorization_policy"] == "transfer-write"
    assert manifest["configuration_keys"] == ["SERVICE_NAME"]
