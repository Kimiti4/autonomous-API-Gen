from app.engine.backend_ir import (
    BackendEndpoint, build_backend_ir, validate_backend_ir,
)


def test_backend_ir_is_technology_neutral():
    ir = build_backend_ir("ARCH-1", source_requirements=("R1",))
    payload = str(ir.to_dict())
    assert all(x not in payload for x in ("FastAPI", "Express", "PostgreSQL", "AWS", "React"))
    assert ir.schema_version == "CAP-003-BackendIR.v1"


def test_backend_ir_requires_explicit_lifecycle_and_error_contract():
    ir = build_backend_ir("ARCH-1", source_requirements=("R1",),
                          error_contract="", lifecycle=())
    findings = validate_backend_ir(ir)
    assert "backend IR has no error contract" in findings
    assert "backend IR has no lifecycle contract" in findings


def test_endpoint_contract_is_validated():
    ir = build_backend_ir("ARCH-1", source_requirements=("R1",),
        endpoints=(BackendEndpoint("EP1", "create", "relative", "TRACE"),))
    findings = validate_backend_ir(ir)
    assert any("absolute" in x for x in findings)
    assert any("unsupported HTTP method" in x for x in findings)
