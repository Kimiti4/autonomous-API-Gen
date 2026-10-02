from app.engine.api_ir import ApiContractIR, ApiOperation
from app.engine.implementation_ir import BackendIR, FrontendIR, DataFlowIR
from app.engine.effect_coherence import EffectPath, verify_effect_coherence

def api():
    return ApiContractIR("1","wallet",(
        ApiOperation("wallet_transfer","POST","/wallets/transfer"),
        ApiOperation("wallet_get","GET","/wallets/{id}"),
    ),"errors")

def test_state_change_requires_explicit_effect_path():
    f=FrontendIR("1","wallet",("/wallets/transfer",),"wallet",
        data_flows=(DataFlowIR("transfer-flow","user","api","wallet","show-error"),))
    b=BackendIR("1","backend:wallet",("wallet",),"wallet")
    findings=verify_effect_coherence(f,api(),b)
    assert any(x.code=="FS-EFFECT-002" for x in findings)

def test_complete_effect_path_is_coherent():
    f=FrontendIR("1","wallet",("/wallets/transfer",),"wallet",
        data_flows=(DataFlowIR("transfer-flow","user","api","wallet","show-error"),))
    b=BackendIR("1","backend:wallet",("wallet",),"wallet")
    e=(EffectPath("wallet_transfer","transfer-flow","wallet","effect:transfer","wallet-auth","ledger+event"),)
    assert not verify_effect_coherence(f,api(),b,e)

def test_unknown_frontend_flow_is_rejected():
    f=FrontendIR("1","wallet",("/wallets/transfer",),"wallet")
    b=BackendIR("1","backend:wallet",("wallet",),"wallet")
    e=(EffectPath("wallet_transfer","missing","wallet","effect:transfer","wallet-auth","ledger"),)
    assert any(x.code=="FS-EFFECT-007" for x in verify_effect_coherence(f,api(),b,e))
