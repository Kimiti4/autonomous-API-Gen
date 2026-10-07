from app.engine.implementation_ir import (
    BackendIR, DataFlowIR, FrontendIR, ModuleIR, backend_from_api, frontend_from_api
)

def test_backend_can_represent_real_architecture():
    ir = BackendIR("1","backend:x",("wallet",),"x",
        modules=(ModuleIR("wallet","wallet domain",invariants=("balance>=0",)),),
        data_flows=(DataFlowIR("f","wallet","ledger","effect","retry-idempotently"),),
        security_boundaries=("wallet-auth",), failure_modes=("db-timeout",))
    d=ir.to_dict()
    assert d["modules"][0]["invariants"] == ["balance>=0"]
    assert d["data_flows"][0]["failure_policy"] == "retry-idempotently"
    assert d["security_boundaries"] == ("wallet-auth",)

def test_frontend_can_represent_real_user_flow():
    ir = FrontendIR("1","frontend:x",("/wallets",),"x",
        modules=(ModuleIR("wallet-page","wallet interaction"),),
        data_flows=(DataFlowIR("f","user","api","wallet-contract","show-error"),),
        security_boundaries=("authenticated-session",),
        failure_states=("loading","empty","error"),
        design_constraints=("keyboard-accessible",))
    d=ir.to_dict()
    assert "error" in d["failure_states"]
    assert d["modules"][0]["responsibility"] == "wallet interaction"
    assert "keyboard-accessible" in d["design_constraints"]
