from app.engine.backend_certification import certify_compiler
from app.engine.backend_contracts import contract_manifest
from app.engine.backend_ir import BackendEndpoint, build_backend_ir
from app.engine.fastapi_compiler import FastAPIBackendCompiler


def test_certification_rejects_current_compiler_when_semantics_are_missing():
    ir = build_backend_ir(
        "ARCH-1", source_requirements=("R1",),
        endpoints=(BackendEndpoint(
            "EP1", "create_transfer", "/transfers", "POST",
            "TransferRequest", "TransferResponse", "transfer-write"
        ),),
        configuration_keys=("SERVICE_NAME",),
    )
    result = certify_compiler(ir, FastAPIBackendCompiler().compile(ir))
    assert not result.certified
    assert result.findings
    assert "operation-contracts-preserved" in result.checks


def test_certification_surface_is_explicit():
    ir = build_backend_ir("ARCH-1", source_requirements=("R1",))
    result = certify_compiler(ir, FastAPIBackendCompiler().compile(ir))
    assert set(result.checks) == {
        "compilation-success", "source-schema-preserved",
        "operation-contracts-preserved", "configuration-contract-preserved",
        "lifecycle-contract-preserved", "error-contract-preserved",
    }
    assert contract_manifest(ir)["schema_version"] == ir.schema_version
