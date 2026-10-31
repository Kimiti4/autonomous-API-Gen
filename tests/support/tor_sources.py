"""Source-bound TOR fixtures shared by projection and runtime evidence."""
from __future__ import annotations

from compiler.core.lowering import isr_to_plan
from compiler.core.plan import CompilationPlan
from reqgraph.adapters.tor_isr import TORISRProjection, project_tor_to_isr
from reqgraph.ingestion.tor_extractor import (
    HumanApproval,
    TORCandidate,
    TORExtractionDraft,
    extract_tor_text,
)

BACKEND_TOR = """1. FUNCTIONAL REQUIREMENTS
- The system shall manage employee payroll records.
- The system shall calculate gross pay from base salary and allowances.
"""

AUTHORIZED_TOR = """1. FUNCTIONAL REQUIREMENTS
- The system shall manage employee payroll records.
- The system shall calculate gross pay from base salary and allowances.
- The system shall restrict employee payroll records to payroll approvers.
"""

FULL_STACK_TOR = """1. FUNCTIONAL REQUIREMENTS
- The system shall manage employee payroll records.
- The system shall calculate gross pay from base salary and allowances.
- The system shall expose a payroll submission API.
- The system shall provide a payroll submission screen.
"""


def candidate(draft: TORExtractionDraft, needle: str) -> TORCandidate:
    matches = [item for item in draft.candidates if needle in item.statement]
    if len(matches) != 1:
        raise AssertionError(f"expected one TOR candidate matching {needle!r}, got {matches}")
    return matches[0]


def approval(
    *,
    nodes: tuple[dict, ...] = (),
    edges: tuple[dict, ...] = (),
) -> HumanApproval:
    return HumanApproval(
        reviewer_id="source-bound-reviewer",
        approval_ref="decision:source-bound-tor",
        acceptance_criteria=("An independently authored test verifies this requirement.",),
        isr_nodes=nodes,
        isr_edges=edges,
    )


def _declaration(
    requirement_id: str,
    node_id: str,
    node_type: str,
    properties: dict,
) -> dict:
    return {
        "id": node_id,
        "type": node_type,
        "properties": {
            **properties,
            "source_requirement_ids": properties.get("source_requirement_ids", [requirement_id]),
        },
    }


def _edge(
    requirement_id: str,
    edge_id: str,
    edge_type: str,
    source_id: str,
    target_id: str,
    source_ids: list[str] | None = None,
) -> dict:
    return {
        "id": edge_id,
        "type": edge_type,
        "source_id": source_id,
        "target_id": target_id,
        "properties": {
            "source_requirement_ids": source_ids or [requirement_id],
        },
    }


def _data_model(requirement_id: str) -> dict:
    return _declaration(
        requirement_id,
        "data:employee",
        "data_model",
        {
            "label": "Employee",
            "behavior": {
                "fields": [
                    {"name": "employee_id", "value_type": "identifier"},
                    {"name": "base_salary", "value_type": "money", "precision": 12, "scale": 2},
                    {"name": "allowances", "value_type": "money", "precision": 12, "scale": 2},
                ],
            },
        },
    )


def _payroll_service(requirement_id: str, data_requirement_id: str) -> tuple[dict, dict]:
    service = _declaration(
        requirement_id,
        "service:payroll",
        "service",
        {
            "label": "Payroll",
            "behavior": {
                "rules": [{
                    "rule_id": "payroll.gross",
                    "description": "Gross pay equals base salary plus allowances.",
                    "expression": {"op": "add", "args": [
                        {"op": "field", "field_ref": "Employee.base_salary"},
                        {"op": "field", "field_ref": "Employee.allowances"},
                    ]},
                }],
                "transitions": [{
                    "transition_id": "payroll.submit",
                    "source_state": "draft",
                    "target_state": "submitted",
                    "guard": {"op": "greater_than", "args": [
                        {"op": "field", "field_ref": "Employee.base_salary"},
                        {"op": "literal", "value": 0},
                    ]},
                }],
            },
            "source_requirement_ids": [requirement_id, data_requirement_id],
        },
    )
    persist = _edge(
        requirement_id,
        "persist:employee",
        "persists",
        "service:payroll",
        "data:employee",
        source_ids=[requirement_id, data_requirement_id],
    )
    return service, persist


def _security_policy(requirement_id: str) -> dict:
    return _declaration(
        requirement_id,
        "security:payroll-approver",
        "security_policy",
        {
            "label": "PayrollApprover",
            "behavior": {
                "roles": ["payroll_approver"],
                "rules": [
                    {
                        "rule_id": "payroll.employee.read",
                        "effect": "allow",
                        "roles": ["payroll_approver"],
                        "actions": ["employee.read", "employee.create", "employee.update"],
                        "resource": "Employee",
                    },
                    {
                        "rule_id": "payroll.employee.delete.deny",
                        "effect": "deny",
                        "roles": ["payroll_approver"],
                        "actions": ["employee.delete"],
                        "resource": "Employee",
                    },
                ],
            },
        },
    )


def _secured_by(requirement_id: str) -> dict:
    return _edge(
        requirement_id,
        "secure:payroll",
        "secured_by",
        "service:payroll",
        "security:payroll-approver",
    )


def _api(requirement_id: str) -> dict:
    return _declaration(
        requirement_id,
        "api:payroll",
        "api",
        {
            "label": "SubmitPayroll",
            "behavior": {
                "operation_id": "payroll.submit",
                "method": "POST",
                "path": "/payroll-runs",
                "request_fields": [
                    {"name": "employee_id", "value_type": "identifier"},
                    {"name": "base_salary", "value_type": "money", "precision": 12, "scale": 2},
                    {"name": "allowances", "value_type": "money", "precision": 12, "scale": 2},
                ],
                "response_fields": [{"name": "status", "value_type": "string"}],
            },
        },
    )


def _frontend(requirement_id: str, api_requirement_id: str) -> tuple[tuple[dict, ...], tuple[dict, ...]]:
    route = _declaration(
        requirement_id,
        "ui:payroll",
        "frontend_route",
        {
            "label": "PayrollPage",
            "behavior": {
                "path": "/payroll",
                "title": "Payroll Management",
                "requires_auth": False,
            },
        },
    )
    interaction = _declaration(
        requirement_id,
        "ui:submit-payroll",
        "frontend_interaction",
        {
            "label": "Submit payroll run",
            "behavior": {
                "label": "Submit payroll run",
                "action": "submit",
                "success_message": "Payroll run submitted",
            },
        },
    )
    edges = (
        _edge(requirement_id, "ui-routes-api", "routes_to", "ui:payroll", "api:payroll",
              source_ids=[requirement_id, api_requirement_id]),
        _edge(requirement_id, "ui-contains-interaction", "contains", "ui:payroll", "ui:submit-payroll"),
        _edge(requirement_id, "ui-invokes-api", "invokes", "ui:submit-payroll", "api:payroll",
              source_ids=[requirement_id, api_requirement_id]),
    )
    return (route, interaction), edges


def backend_projection() -> TORISRProjection:
    draft = extract_tor_text(BACKEND_TOR, "payroll-backend-tor.md")
    manage = candidate(draft, "manage employee payroll records")
    calculate = candidate(draft, "calculate gross pay")
    service, persist = _payroll_service(calculate.requirement_id, manage.requirement_id)
    approvals = {
        manage.requirement_id: approval(nodes=(_data_model(manage.requirement_id),)),
        calculate.requirement_id: approval(nodes=(service,), edges=(persist,)),
    }
    return project_tor_to_isr(
        draft,
        approvals,
        system_id="payroll-backend-source",
        revision_id="rev-backend-source-1",
        created_at="2026-01-01T00:00:00Z",
    )


def full_stack_projection() -> TORISRProjection:
    draft = extract_tor_text(FULL_STACK_TOR, "payroll-tor.md")
    manage = candidate(draft, "manage employee payroll records")
    calculate = candidate(draft, "calculate gross pay")
    expose = candidate(draft, "expose a payroll submission API")
    screen = candidate(draft, "provide a payroll submission screen")
    service, persist = _payroll_service(calculate.requirement_id, manage.requirement_id)
    frontend_nodes, frontend_edges = _frontend(screen.requirement_id, expose.requirement_id)
    approvals = {
        manage.requirement_id: approval(nodes=(_data_model(manage.requirement_id),)),
        calculate.requirement_id: approval(nodes=(service,), edges=(persist,)),
        expose.requirement_id: approval(nodes=(_api(expose.requirement_id),)),
        screen.requirement_id: approval(nodes=frontend_nodes, edges=frontend_edges),
    }
    return project_tor_to_isr(
        draft,
        approvals,
        system_id="payroll-full-stack-source",
        revision_id="rev-full-stack-source-1",
        created_at="2026-01-01T00:00:00Z",
    )


def backend_plan() -> CompilationPlan:
    return isr_to_plan(backend_projection().revision)


def authorized_backend_projection() -> TORISRProjection:
    """A source-bound projection that declares a typed authorization policy."""
    draft = extract_tor_text(AUTHORIZED_TOR, "payroll-authorized-tor.md")
    manage = candidate(draft, "manage employee payroll records")
    calculate = candidate(draft, "calculate gross pay")
    restrict = candidate(draft, "restrict employee payroll records")
    service, persist = _payroll_service(calculate.requirement_id, manage.requirement_id)
    approvals = {
        manage.requirement_id: approval(nodes=(_data_model(manage.requirement_id),)),
        calculate.requirement_id: approval(nodes=(service,), edges=(persist,)),
        restrict.requirement_id: approval(
            nodes=(_security_policy(restrict.requirement_id),),
            edges=(_secured_by(restrict.requirement_id),),
        ),
    }
    return project_tor_to_isr(
        draft,
        approvals,
        system_id="payroll-authorized-source",
        revision_id="rev-authorized-source-1",
        created_at="2026-01-01T00:00:00Z",
    )


def authorized_backend_plan() -> CompilationPlan:
    return isr_to_plan(authorized_backend_projection().revision)


def full_stack_plan() -> CompilationPlan:
    return isr_to_plan(full_stack_projection().revision)
