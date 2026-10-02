from app.engine.backend_ir import BackendEndpoint, build_backend_ir
from app.engine.express_compiler import ExpressBackendCompiler
from app.engine.fastapi_compiler import FastAPIBackendCompiler
from app.engine.backend_deep_equivalence import (
    contract_from_ir, verify_deep_backend_equivalence,
)


def test_deep_equivalence_preserves_contract_obligations():
    ir = build_backend_ir(
        "ARCH-1",
        source_requirements=("R1",),
        endpoints=(BackendEndpoint(
            "EP1", "create_transfer", "/transfers", "POST",
            request_schema="TransferRequest",
            response_schema="TransferResponse",
            authorization_policy="transfer-write",
        ),),
        configuration_keys=("SERVICE_NAME",),
    )
    # The current concrete compilers do not yet lower schema/policy names, so
    # deep equivalence correctly remains bounded rather than falsely certified.
    left = FastAPIBackendCompiler().compile(ir)
    right = ExpressBackendCompiler().compile(ir)
    result = verify_deep_backend_equivalence(ir, left, right)
    assert not result.equivalent
    assert any("request schema" in x for x in result.findings)
    assert contract_from_ir(ir).configuration_keys == ("SERVICE_NAME",)


def test_deep_equivalence_passes_for_current_contract_surface():
    ir = build_backend_ir(
        "ARCH-1",
        source_requirements=("R1",),
        endpoints=(BackendEndpoint("EP1", "create_transfer", "/transfers", "POST"),),
    )
    left = FastAPIBackendCompiler().compile(ir)
    right = ExpressBackendCompiler().compile(ir)
    result = verify_deep_backend_equivalence(ir, left, right)
    assert result.equivalent
