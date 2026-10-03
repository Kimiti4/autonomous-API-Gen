from app.engine.verification_compiler import adapter_for, build_verification_plan
from app.engine.verification_obligations import VerificationObligation
from app.engine.verification_artifacts import compile_verification_artifacts, record_execution

def test_compiles_obligation_into_target_artifact():
    o=VerificationObligation("x","idempotency","transfer","repeat","one effect")
    p=build_verification_plan((o,))
    a=compile_verification_artifacts(p,adapter_for("swift"))
    assert a[0].artifact_id == "swift:x"
    assert a[0].executor_kind == "target-test-runner"
    assert "runtime_identity" in a[0].evidence_schema

def test_execution_requires_runtime_identity():
    o=VerificationObligation("x","contract","transfer","valid input","contract behavior")
    a=compile_verification_artifacts(build_verification_plan((o,)),adapter_for("node"))[0]
    try:
        record_execution(a,"passed","ok")
        assert False
    except ValueError:
        pass

def test_execution_is_evidence_bearing():
    o=VerificationObligation("x","contract","transfer","valid input","contract behavior")
    a=compile_verification_artifacts(build_verification_plan((o,)),adapter_for("python"))[0]
    e=record_execution(a,"passed","accepted",("schema matched",),"build:abc")
    assert e.status == "passed"
    assert "runtime_identity=build:abc" in e.evidence
