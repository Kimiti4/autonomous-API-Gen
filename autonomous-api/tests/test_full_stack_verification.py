from app.engine.api_ir import ApiContractIR, ApiOperation
from app.engine.implementation_ir import BackendIR, FrontendIR, DataFlowIR
from app.engine.effect_coherence import EffectPath
from app.engine.effect_consequences import EffectConsequence
from app.engine.full_stack_verification import verify_full_stack

def setup():
    api=ApiContractIR("1","wallet",(ApiOperation("transfer","POST","/transfer"),),"errors")
    f=FrontendIR("1","wallet",("/transfer",),"wallet",
        data_flows=(DataFlowIR("transfer-ui","user","api","wallet","error"),))
    b=BackendIR("1","backend:wallet",("wallet",),"wallet")
    e=(EffectPath("transfer","transfer-ui","wallet","effect:transfer","wallet-auth","ledger"),)
    c=(EffectConsequence("effect:transfer","ledger","transfer.created","transfer-id","unique transfer-id","retry same key","serialize account","reconcile"),)
    return f,api,b,e,c

def test_full_stack_gate_passes_for_coherent_flow():
    f,a,b,e,c=setup()
    v=verify_full_stack(f,a,b,e,c)
    assert v.passed
    assert not v.findings

def test_full_stack_gate_exposes_effect_failure():
    f,a,b,e,c=setup()
    v=verify_full_stack(f,a,b,e,())
    assert not v.passed
    assert any(x.code=="EFFECT-CONS-001" for x in v.findings)
