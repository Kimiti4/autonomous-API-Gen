from app.engine.api_ir import ApiContractIR, ApiOperation
from app.engine.implementation_ir import BackendIR, FrontendIR, DataFlowIR

from app.engine.cross_layer_coherence import verify_cross_layer_coherence

def api():
    return ApiContractIR("1","wallet",(ApiOperation("create","POST","/wallets",idempotency_required=True),),"errors")

def test_detects_orphan_frontend_route():
    f=FrontendIR("1","wallet",("/wallets","/missing"),"wallet")
    b=BackendIR("1","backend:wallet",("wallet",),"wallet",failure_modes=("idempotency supported",))
    findings=verify_cross_layer_coherence(f,api(),b)
    assert any(x.code=="FS-CONTRACT-003" for x in findings)

def test_detects_missing_backend_idempotency_evidence():
    f=FrontendIR("1","wallet",("/wallets",),"wallet")
    b=BackendIR("1","backend:wallet",("wallet",),"wallet")
    findings=verify_cross_layer_coherence(f,api(),b)
    assert any(x.code=="FS-EFFECT-001" for x in findings)

def test_matching_contract_and_idempotency_is_coherent():
    f=FrontendIR("1","wallet",("/wallets",),"wallet")
    b=BackendIR("1","backend:wallet",("wallet",),"wallet",failure_modes=("idempotency supported",))
    assert not verify_cross_layer_coherence(f,api(),b)
