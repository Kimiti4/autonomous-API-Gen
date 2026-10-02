from app.engine.api_ir import ApiContractIR, ApiOperation
from app.engine.implementation_ir import backend_from_api, frontend_from_api

def api():
    return ApiContractIR("1","wallet",(
      ApiOperation("wallet_create","POST","/wallets"),
      ApiOperation("wallet_get","GET","/wallets/{id}"),
    ),"errors")

def test_frontend_and_backend_ir_derive_from_same_contract():
    a=api()
    be=backend_from_api(a,("BE-API",))
    fe=frontend_from_api(a,("FE-COR",))
    assert be.api_contract_id == fe.api_contract_id == "wallet"
    assert "/wallets/{id}" in fe.routes
    assert "wallet" in be.domain_modules

def test_irs_do_not_select_frameworks():
    a=api()
    assert "fastapi" not in str(backend_from_api(a).to_dict()).lower()
    assert "react" not in str(frontend_from_api(a).to_dict()).lower()
