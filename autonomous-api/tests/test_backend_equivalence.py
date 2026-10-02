from app.engine.backend_ir import BackendEndpoint, build_backend_ir
from app.engine.express_compiler import ExpressBackendCompiler
from app.engine.fastapi_compiler import FastAPIBackendCompiler
from app.engine.backend_equivalence import contract_from_ir, verify_backend_equivalence


def test_same_ir_produces_equivalent_api_contracts_across_targets():
    ir = build_backend_ir(
        "ARCH-1",
        source_requirements=("R1",),
        endpoints=(BackendEndpoint("EP1", "create_transfer", "/transfers", "POST"),),
    )
    left = FastAPIBackendCompiler().compile(ir)
    right = ExpressBackendCompiler().compile(ir)
    result = verify_backend_equivalence(ir, left, right)
    assert result.equivalent
    assert contract_from_ir(ir).operations == (("POST", "/transfers", "create_transfer"),)


def test_equivalence_fails_when_a_target_drops_an_operation():
    ir = build_backend_ir(
        "ARCH-1",
        source_requirements=("R1",),
        endpoints=(BackendEndpoint("EP1", "create_transfer", "/transfers", "POST"),),
    )
    left = FastAPIBackendCompiler().compile(ir)
    right = ExpressBackendCompiler().compile(ir)
    broken = type(right)(
        right.target, right.source_schema_version,
        tuple(a for a in right.artifacts if a.path != "app.js"), right.diagnostics
    )
    result = verify_backend_equivalence(ir, left, broken)
    assert not result.equivalent
    assert result.findings
