"""Authoritative payroll proving-case ISR and requirements (derived from governed TOR excerpt).

Used by readiness tests and Checkpoint 045 — not a hand-crafted “completed product” stub.
"""
from __future__ import annotations

from isr.core.graph import Edge, EdgeType, ISRGraph, Node, NodeType
from isr.core.identity import Provenance
from isr.core.revision import ISRRevision
from reqgraph.adapters.isr_projection import merge_requirement_projection
from reqgraph.core.graph import RequirementGraph, RequirementKind
from reqgraph.ingestion.tor_extractor import HumanApproval, extract_tor_text

TOR_EXCERPT = """FUNCTIONAL REQUIREMENTS
- The system shall calculate gross pay from base salary and allowances.
- The system shall support statutory tax and deduction calculations.
"""

CANDIDATE_ID = "world-concern-payroll-cp045"
REVISION_ID = "rev-payroll-candidate-1"


def approved_payroll_requirements() -> RequirementGraph:
    draft = extract_tor_text(TOR_EXCERPT, "world-concern-payroll-tor-excerpt.txt")
    approvals = {
        item.requirement_id: HumanApproval(
            reviewer_id="payroll-requirements-review",
            approval_ref=f"review:{item.requirement_id}",
            acceptance_criteria=(
                "The generated application passes an independently authored test for this requirement.",
            ),
            selected_kind=RequirementKind.FUNCTIONAL,
            resolution_ref=f"resolved:{item.requirement_id}" if item.ambiguity_score >= 0.5 else None,
        )
        for item in draft.candidates
    }
    return draft.approve(approvals)


def payroll_isr_revision() -> ISRRevision:
    nodes = {
        "data:employee": Node(id="data:employee", type=NodeType.DATA_MODEL, properties={
            "label": "Employee",
            "behavior": {"fields": [
                {"name": "employee_id", "value_type": "identifier"},
                {"name": "base_salary", "value_type": "money", "precision": 12, "scale": 2},
                {"name": "allowances", "value_type": "money", "precision": 12, "scale": 2},
            ]},
        }),
        "data:payroll-run": Node(id="data:payroll-run", type=NodeType.DATA_MODEL, properties={
            "label": "PayrollRun",
            "behavior": {"fields": [
                {"name": "run_id", "value_type": "identifier"},
                {"name": "gross_pay", "value_type": "money", "precision": 12, "scale": 2},
                {"name": "status", "value_type": "string"},
            ]},
        }),
        "service:payroll": Node(id="service:payroll", type=NodeType.SERVICE, properties={
            "label": "Payroll",
            "behavior": {"rules": [{
                "rule_id": "payroll.gross",
                "description": "Gross pay is base salary plus allowances.",
                "expression": {"op": "add", "args": [
                    {"op": "field", "field_ref": "Employee.base_salary"},
                    {"op": "field", "field_ref": "Employee.allowances"},
                ]},
            }]},
        }),
        "event:payroll-submitted": Node(id="event:payroll-submitted", type=NodeType.EVENT, properties={
            "label": "PayrollSubmitted",
            "behavior": {"fields": [{"name": "run_id", "value_type": "identifier"}]},
        }),
        "api:submit-payroll": Node(id="api:submit-payroll", type=NodeType.API, properties={
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
                "response_fields": [{"name": "gross_pay", "value_type": "money", "precision": 12, "scale": 2}],
                "authorization_policy_ids": ["security:payroll"],
            },
        }),
        "security:payroll": Node(id="security:payroll", type=NodeType.SECURITY_POLICY, properties={
            "label": "PayrollAuthorization",
            "behavior": {"roles": ["payroll_admin", "payroll_approver"], "rules": [{
                "rule_id": "payroll-submit-approver",
                "effect": "allow",
                "roles": ["payroll_approver"],
                "actions": ["payroll.submit"],
                "resource": "PayrollRun",
            }]},
        }),
        "effect:bank-transfer": Node(id="effect:bank-transfer", type=NodeType.EFFECT, properties={
            "label": "BankTransfer",
            "behavior": {"effect_kind": "bank_transfer", "idempotent": True, "idempotency_key_required": True},
        }),
        "invariant:nonnegative-salary": Node(id="invariant:nonnegative-salary", type=NodeType.INVARIANT, properties={
            "label": "NonnegativeSalary",
            "behavior": {
                "invariant_id": "payroll.salary.nonnegative",
                "description": "Base salary must be nonnegative.",
                "expression": {"op": "greater_or_equal", "args": [
                    {"op": "field", "field_ref": "Employee.base_salary"},
                    {"op": "literal", "value": 0},
                ]},
            },
        }),
        "frontend:payroll": Node(id="frontend:payroll", type=NodeType.FRONTEND_ROUTE, properties={
            "label": "PayrollPage",
            "behavior": {"path": "/payroll", "title": "Payroll Management", "requires_auth": False},
        }),
        "interaction:submit": Node(id="interaction:submit", type=NodeType.FRONTEND_INTERACTION, properties={
            "label": "Submit payroll run",
            "behavior": {"label": "Submit payroll run", "action": "submit", "success_message": "Payroll run submitted"},
        }),
    }
    edges = {
        "persist-employee": Edge(id="persist-employee", type=EdgeType.PERSISTS, source_id="service:payroll", target_id="data:employee"),
        "persist-run": Edge(id="persist-run", type=EdgeType.PERSISTS, source_id="service:payroll", target_id="data:payroll-run"),
        "publish-event": Edge(id="publish-event", type=EdgeType.PUBLISHES, source_id="service:payroll", target_id="event:payroll-submitted"),
        "expose-api": Edge(id="expose-api", type=EdgeType.EXPOSES, source_id="service:payroll", target_id="api:submit-payroll"),
        "secure-service": Edge(id="secure-service", type=EdgeType.SECURED_BY, source_id="service:payroll", target_id="security:payroll"),
        "secure-api": Edge(id="secure-api", type=EdgeType.SECURED_BY, source_id="api:submit-payroll", target_id="security:payroll"),
        "cause-effect": Edge(id="cause-effect", type=EdgeType.CAUSES_EFFECT, source_id="service:payroll", target_id="effect:bank-transfer"),
        "require-invariant": Edge(id="require-invariant", type=EdgeType.REQUIRES_INVARIANT, source_id="service:payroll", target_id="invariant:nonnegative-salary"),
        "route-api": Edge(id="route-api", type=EdgeType.ROUTES_TO, source_id="frontend:payroll", target_id="api:submit-payroll"),
        "route-interaction": Edge(id="route-interaction", type=EdgeType.CONTAINS, source_id="frontend:payroll", target_id="interaction:submit"),
        "invoke-api": Edge(id="invoke-api", type=EdgeType.INVOKES, source_id="interaction:submit", target_id="api:submit-payroll"),
    }
    base = ISRGraph(nodes=nodes, edges=edges)
    merged = merge_requirement_projection(base, approved_payroll_requirements())
    return ISRRevision.create(
        "world-concern-payroll",
        REVISION_ID,
        "1.0",
        merged,
        Provenance(created_by="payroll-proving-case", created_at="2026-01-01T00:00:00Z"),
    )
