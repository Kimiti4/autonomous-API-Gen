"""Tests for ISR-derived React frontend compilation and its fail-closed boundary."""
from __future__ import annotations

from compiler.backends.react_frontend import ReactFrontendBackend
from compiler.core.capabilities import UnsupportedSemanticsError
from compiler.core.lowering import isr_to_plan
from isr.core.graph import Edge, EdgeType, ISRGraph, Node, NodeType
from isr.core.identity import Provenance
from isr.core.revision import ISRRevision


def _revision(requires_auth: bool = False) -> ISRRevision:
    nodes = {
        "api:submit-payroll": Node(id="api:submit-payroll", type=NodeType.API, properties={
            "label": "SubmitPayroll",
            "behavior": {
                "operation_id": "payroll.submit",
                "method": "POST",
                "path": "/payroll-runs",
                "request_fields": [
                    {"name": "employee_id", "value_type": "identifier"},
                    {"name": "gross_pay", "value_type": "money", "precision": 12, "scale": 2},
                ],
                "response_fields": [{"name": "status", "value_type": "string"}],
            },
        }),
        "frontend:payroll-page": Node(id="frontend:payroll-page", type=NodeType.FRONTEND_ROUTE, properties={
            "label": "PayrollPage",
            "behavior": {
                "path": "/payroll",
                "title": "Payroll Management",
                "requires_auth": requires_auth,
            },
        }),
        "interaction:submit-payroll": Node(id="interaction:submit-payroll", type=NodeType.FRONTEND_INTERACTION, properties={
            "label": "Submit payroll run",
            "behavior": {
                "label": "Submit payroll run",
                "action": "submit",
                "success_message": "Payroll run submitted",
            },
        }),
    }
    edges = {
        "route-api": Edge(id="route-api", type=EdgeType.ROUTES_TO, source_id="frontend:payroll-page", target_id="api:submit-payroll"),
        "route-interaction": Edge(id="route-interaction", type=EdgeType.CONTAINS, source_id="frontend:payroll-page", target_id="interaction:submit-payroll"),
        "interaction-api": Edge(id="interaction-api", type=EdgeType.INVOKES, source_id="interaction:submit-payroll", target_id="api:submit-payroll"),
    }
    return ISRRevision.create(
        "payroll-frontend",
        "rev-frontend-1",
        "1.0",
        ISRGraph(nodes=nodes, edges=edges),
        Provenance(created_by="frontend-compiler-test", created_at="2025-01-01T00:00:00Z"),
    )


def test_frontend_projection_preserves_route_interaction_and_api_contract():
    plan = isr_to_plan(_revision())
    route = plan.frontend_routes[0]
    assert route.behavior.path == "/payroll"
    assert route.behavior.title == "Payroll Management"
    assert route.api_operations[0].behavior.operation_id == "payroll.submit"
    interaction = route.interactions[0]
    assert interaction.behavior.action == "submit"
    assert interaction.target_api_operation.behavior.method == "POST"
    assert [field.name for field in interaction.target_api_operation.behavior.request_fields] == [
        "employee_id", "gross_pay"
    ]


def test_react_frontend_emits_runnable_app_and_behavioral_test_suite():
    plan = isr_to_plan(_revision())
    repo = ReactFrontendBackend().compile(plan)
    assert {"package.json", "index.html", "vite.config.ts", "tsconfig.json", "src/main.tsx", "src/App.tsx", "src/App.test.tsx", "src/style.css"} <= set(repo.files)
    app = repo.files["src/App.tsx"]
    tests = repo.files["src/App.test.tsx"]
    package = repo.files["package.json"]
    assert "Payroll Management" in app
    assert "POST" in app
    assert "/payroll-runs" in app
    assert "fetch(path" in app
    assert "calls the declared API" in tests
    assert "vitest" in package
    assert "vite build" in package


def test_auth_required_route_fails_closed_until_authentication_flow_exists():
    plan = isr_to_plan(_revision(requires_auth=True))
    try:
        ReactFrontendBackend().compile(plan)
    except UnsupportedSemanticsError as exc:
        assert "authentication flow" in str(exc)
    else:
        raise AssertionError("frontend compiler must not silently omit an auth requirement")


def test_route_or_interaction_without_typed_contract_is_not_emitted_as_a_stub():
    from compiler.core.plan import CompilationPlan, FrontendRoute

    plan = CompilationPlan(
        plan_id="plan:missing-route-contract",
        isr_id="missing-route-contract",
        frontend_routes=[FrontendRoute(id="route:missing", name="Missing", behavior=None)],
    )
    try:
        ReactFrontendBackend().compile(plan)
    except UnsupportedSemanticsError as exc:
        assert "typed route payload" in str(exc)
    else:
        raise AssertionError("frontend compiler must reject untyped route stubs")
