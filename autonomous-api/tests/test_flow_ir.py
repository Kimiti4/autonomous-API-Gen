from app.engine.flow_ir import *

def test_flow_requires_existing_nodes():
    f=FlowIR("A",(FlowNode("ui","frontend","submit"),),(FlowEdge("ui","missing","sync"),))
    assert "missing-target:missing" in validate_flow(f)

def test_async_semantics_are_explicit():
    f=FlowIR("A",(FlowNode("a","backend","publish"),FlowNode("b","backend","consume")),
             (FlowEdge("a","b","event",delivery="at-least-once"),))
    assert validate_flow(f)==()

def test_retries_require_idempotency():
    f=FlowIR("A",(),(),(FailureRecovery("r","timeout","retry",3,False),))
    assert "retry-without-idempotency:r" in validate_flow(f)

def test_flow_must_match_authoritative_architecture():
    f=FlowIR("A",(),())
    assert verify_flow_references(f,"B")==("architecture-id-mismatch",)
