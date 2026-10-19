from __future__ import annotations

import json

from app.engine.frontend_ir import (
    FrontendActionBinding,
    FrontendProjectIR,
    FrontendScreen,
    validate_frontend_ir,
)
from app.engine.react_typescript_compiler import ReactTypeScriptCompiler


def _ir(binding: bool = True) -> FrontendProjectIR:
    screen = FrontendScreen(
        "payroll",
        "/payroll",
        "Payroll Dashboard",
        "PayrollRunList",
        "payroll.read",
        ("Refresh payroll runs", "View payslips"),
        ("keyboard-navigation", "screen-reader"),
        (
            FrontendActionBinding(
                "Refresh payroll runs",
                "payroll.list_runs",
                "GET",
                "/api/payroll-runs",
                (),
                "payroll.read",
            ),
        ) if binding else (),
    )
    return FrontendProjectIR(
        "1", "payroll-ui", (screen,), "api-v1",
        ("responsive-layout", "semantic-html"), ("API_BASE_URL",),
    )


def test_compiler_emits_complete_buildable_react_project():
    compilation = ReactTypeScriptCompiler().compile(_ir())
    assert compilation.diagnostics == ()
    files = {artifact.path: artifact.content for artifact in compilation.artifacts}
    required = {
        "package.json", "index.html", "vite.config.ts", "tsconfig.json",
        "playwright.config.ts", "src/main.tsx", "src/App.tsx",
        "src/App.test.tsx", "e2e/generated-app.spec.ts", "src/contracts.json",
    }
    assert required <= set(files)
    package = json.loads(files["package.json"])
    assert package["scripts"]["build"] == "tsc --noEmit && vite build"
    assert package["scripts"]["test"] == "vitest run"
    assert package["scripts"]["test:e2e"] == "playwright test"
    assert "createRoot" in files["src/main.tsx"]
    assert "keyboard-navigation" in files["src/contracts.json"]


def test_bound_action_calls_declared_api_and_reports_actual_http_result():
    compilation = ReactTypeScriptCompiler().compile(_ir())
    files = {artifact.path: artifact.content for artifact in compilation.artifacts}
    app = files["src/App.tsx"]
    assert 'api_operation_id' in app
    assert "/api/payroll-runs" in app
    assert "await fetch" in app
    assert "Request completed:" in app
    assert "Request rejected:" in app
    assert "Request failed: API unavailable" in app
    assert "Access policy: payroll.read. The API remains authoritative" in app
    assert "Request completed" in files["e2e/generated-app.spec.ts"]


def test_unbound_action_never_claims_an_api_operation_succeeded():
    compilation = ReactTypeScriptCompiler().compile(_ir(binding=False))
    files = {artifact.path: artifact.content for artifact in compilation.artifacts}
    app = files["src/App.tsx"]
    assert "no API binding configured" in app
    assert "await fetch" not in app
    assert "no API binding configured" in files["e2e/generated-app.spec.ts"]


def test_invalid_action_binding_fails_closed():
    ir = FrontendProjectIR(
        "1", "payroll-ui",
        (FrontendScreen(
            "payroll", "/payroll", "Payroll",
            actions=("Refresh",),
            action_bindings=(FrontendActionBinding(
                "Refresh", "missing-operation", "TRACE", "api/payroll", (), None
            ),),
        ),),
        "api-v1",
    )
    findings = validate_frontend_ir(ir)
    assert any("unsupported API method" in finding for finding in findings)
    assert any("must start with '/'" in finding for finding in findings)
    assert ReactTypeScriptCompiler().compile(ir).diagnostics
