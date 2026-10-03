from app.engine.api_ir import ApiContractIR, ApiOperation
from app.engine.implementation_ir import BackendIR, FrontendIR, DataFlowIR

from app.engine.verification_obligations import derive_verification_obligations
from app.engine.effect_coherence import EffectPath
from app.engine.effect_consequences import EffectConsequence

def test_state_change_generates_safety_obligations():
    a=ApiContractIR("1","wallet",(ApiOperation("transfer","POST","/transfer"),),"errors")
    f=FrontendIR("1","wallet",("/transfer",),"wallet",
        interaction_flows=("transfer-ui",),
        data_flows=(DataFlowIR("transfer-flow","ui","api","wallet","show-error"),))
    b=BackendIR("1","backend:wallet",("wallet",),"wallet")
    e=(EffectPath("transfer","transfer-flow","wallet","effect:transfer","wallet-auth","ledger"),)
    c=(EffectConsequence("effect:transfer","ledger","transfer.created","transfer-id","unique transfer-id","retry same key","serialize","reconcile"),)
    ids={x.obligation_id for x in derive_verification_obligations(f,a,b,e,c)}
    assert "VERIFY-AUTH-transfer" in ids
    assert "VERIFY-REPLAY-transfer" in ids
    assert "VERIFY-CONCURRENCY-transfer" in ids
    assert "VERIFY-RECOVERY-transfer" in ids
    assert "VERIFY-EVENT-effect:transfer" in ids

def test_read_only_operation_still_generates_contract_verification():
    a=ApiContractIR("1","x",(ApiOperation("get","GET","/x"),),"errors")
    f=FrontendIR("1","x",("/x",),"x")
    b=BackendIR("1","backend:x",("x",),"x")
    o=derive_verification_obligations(f,a,b)
    assert [x.obligation_id for x in o] == ["VERIFY-CONTRACT-get"]
