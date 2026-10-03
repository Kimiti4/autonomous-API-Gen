from app.engine.rich_architecture_ir import *

def test_frontend_requires_interaction_outcomes():
    i=FrontendIR("A",("Dashboard",),(),(FrontendInteraction("click","tap",""),),())
    assert "click:missing-outcome" in validate_frontend_ir(i)

def test_backend_requires_authority_and_concurrency_policy():
    b=BackendIR("A",(BackendBoundary("B","wallet","","trusted",""),),())
    errors=validate_backend_ir(b)
    assert "B:missing-authority" in errors
    assert "B:missing-concurrency-policy" in errors

def test_cross_layer_contract_and_invariant_alignment():
    c=DataContract("swap.create","request","SwapCreate","required")
    f=FrontendIR("A",("Swap",),(),(),(c,),("swap-idempotent",))
    b=BackendIR("A",(BackendBoundary("svc","swap","swap-db","trusted","serialized"),),(c,),("swap-idempotent",))
    assert verify_cross_layer_contracts(f,b)==()

def test_cross_layer_mismatch_is_explicit():
    c=DataContract("x","request","X")
    f=FrontendIR("A",(),(),(),(c,),("i1",))
    b=BackendIR("B",(),(),())
    errors=verify_cross_layer_contracts(f,b)
    assert "architecture-id-mismatch" in errors
    assert "missing-backend-contract:x" in errors
    assert "invariant-not-shared:i1" in errors
