from app.engine.api_contract_bindings import verify_api_contract_bindings
from app.engine.api_ir import ApiContractIR, ApiOperation
from app.engine.backend_ir import BackendEndpoint, build_backend_ir
from app.engine.frontend_ir import FrontendActionBinding, FrontendProjectIR, FrontendScreen
from app.engine.schema_ir import SchemaField, SchemaIR


def test_canonical_api_binds_backend_and_frontend():
    api = ApiContractIR("1", "wallet-api", (
        ApiOperation("wallet", "GET", "/wallet", None, "WalletView", "wallet-read"),
    ), "stable errors")
    backend = build_backend_ir("A1", source_requirements=("R1",), endpoints=(
        BackendEndpoint("E1", "wallet", "/wallet", "GET", None, "WalletView", "wallet-read"),
    ))
    frontend = FrontendProjectIR("1", "app", (
        FrontendScreen("wallet", "/wallet", "Wallet", "WalletView", "wallet-read", ("refresh",)),
    ), "v1")
    assert verify_api_contract_bindings(api, backend, frontend) == ()


def test_binding_rejects_backend_schema_drift():
    api = ApiContractIR("1", "wallet-api", (
        ApiOperation("wallet", "GET", "/wallet", None, "WalletView", "wallet-read"),
    ), "stable errors")
    backend = build_backend_ir("A1", source_requirements=("R1",), endpoints=(
        BackendEndpoint("E1", "wallet", "/wallet", "GET", None, "WrongView", "wallet-read"),
    ))
    frontend = FrontendProjectIR("1", "app", (
        FrontendScreen("wallet", "/wallet", "Wallet", "WalletView", "wallet-read", ("refresh",)),
    ), "v1")
    findings = verify_api_contract_bindings(api, backend, frontend)
    assert any("response schema mismatch" in x for x in findings)



def test_explicit_action_binding_matches_canonical_api_operation():
    api = ApiContractIR("1", "payroll-api", (
        ApiOperation("payroll.list_runs", "GET", "/api/payroll-runs", None, "PayrollRunList", "payroll.read"),
    ), "stable errors")
    backend = build_backend_ir("A1", source_requirements=("R1",), endpoints=(
        BackendEndpoint("E1", "payroll.list_runs", "/api/payroll-runs", "GET", None, "PayrollRunList", "payroll.read"),
    ))
    frontend = FrontendProjectIR("1", "payroll-app", (
        FrontendScreen(
            "payroll", "/payroll", "Payroll", "PayrollRunList", "payroll.read",
            ("refresh", "view-payslips"), ("keyboard-navigation", "screen-reader"),
            (FrontendActionBinding("refresh", "payroll.list_runs", "GET", "/api/payroll-runs", (), "payroll.read"),),
        ),
    ), "v1")
    assert verify_api_contract_bindings(api, backend, frontend) == ()


def test_explicit_action_binding_rejects_unknown_operation_and_path_drift():
    api = ApiContractIR("1", "payroll-api", (
        ApiOperation("payroll.list_runs", "GET", "/api/payroll-runs", None, "PayrollRunList", "payroll.read"),
    ), "stable errors")
    backend = build_backend_ir("A1", source_requirements=("R1",), endpoints=(
        BackendEndpoint("E1", "payroll.list_runs", "/api/payroll-runs", "GET", None, "PayrollRunList", "payroll.read"),
    ))
    frontend = FrontendProjectIR("1", "payroll-app", (
        FrontendScreen(
            "payroll", "/payroll", "Payroll", "PayrollRunList", "payroll.read",
            ("refresh", "view-payslips"), ("keyboard-navigation", "screen-reader"),
            (FrontendActionBinding("refresh", "payroll.unknown", "GET", "/api/other", (), "payroll.read"),),
        ),
    ), "v1")
    findings = verify_api_contract_bindings(api, backend, frontend)
    assert any("unknown API operation" in finding for finding in findings)


def test_explicit_action_binding_must_supply_required_request_fields():
    api = ApiContractIR("1", "payroll-api", (
        ApiOperation("payroll.create_run", "POST", "/api/payroll-runs", "PayrollRunInput", "PayrollRun", "payroll.write"),
    ), "stable errors", schemas=(
        SchemaIR("PayrollRunInput", fields=(SchemaField("period", "string"),)),
        SchemaIR("PayrollRun", fields=(SchemaField("run_id", "string"),)),
    ))
    backend = build_backend_ir("A1", source_requirements=("R1",), endpoints=(
        BackendEndpoint("E1", "payroll.create_run", "/api/payroll-runs", "POST", "PayrollRunInput", "PayrollRun", "payroll.write"),
    ))
    frontend = FrontendProjectIR("1", "payroll-app", (
        FrontendScreen(
            "payroll", "/payroll", "Payroll", "PayrollRun", "payroll.write",
            ("create", "view"), ("keyboard-navigation", "screen-reader"),
            (FrontendActionBinding("create", "payroll.create_run", "POST", "/api/payroll-runs", (), "payroll.write"),),
        ),
    ), "v1")
    findings = verify_api_contract_bindings(api, backend, frontend)
    assert any("omits required request fields" in finding for finding in findings)
