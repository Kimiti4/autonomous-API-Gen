"""Payroll proving case: source requirements, ISR, compiler gates, and honest status."""
from __future__ import annotations

from compiler.backends.python_fastapi import PythonFastAPIBackend
from compiler.backends.react_frontend import ReactFrontendBackend
from compiler.backends.rust_axum import RustAxumBackend
from compiler.core.capabilities import BackendCapabilities, UnsupportedSemanticsError
from compiler.core.lowering import isr_to_plan
from certification.payroll.readiness import assess_payroll_readiness
from isr.core.graph import Edge, EdgeType, ISRGraph, Node, NodeType
from isr.core.identity import Provenance
from isr.core.revision import ISRRevision
from reqgraph.adapters.isr_projection import merge_requirement_projection
from reqgraph.core.graph import RequirementKind
from reqgraph.ingestion.tor_extractor import HumanApproval, extract_tor_text


TOR_EXCERPT = """FUNCTIONAL REQUIREMENTS
- The system shall calculate gross pay from base salary and allowances.
- The system shall support statutory tax and deduction calculations.
"""


def _approved_requirements():
    draft = extract_tor_text(TOR_EXCERPT, "world-concern-payroll-tor-excerpt.txt")
    approvals = {
        item.requirement_id: HumanApproval(
            reviewer_id="payroll-requirements-review",
            approval_ref=f"review:{item.requirement_id}",
            acceptance_criteria=(
                "The generated application passes an independently authored test for this requirement.",
            ),
            selected_kind=RequirementKind.FUNCTIONAL,
            resolution_ref=f"resolved:{item.requirement_id}" if item.ambiguity_score > 0.5 else None,
        )
        for item in draft.candidates
    }
    return draft.approve(approvals)


def _payroll_revision():
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
    merged = merge_requirement_projection(base, _approved_requirements())
    return ISRRevision.create(
        "world-concern-payroll",
        "rev-payroll-candidate-1",
        "1.0",
        merged,
        Provenance(created_by="payroll-readiness-test", created_at="2026-01-01T00:00:00Z"),
    )


def test_payroll_plan_preserves_behavior_but_is_not_misreported_as_certified():
    requirements = _approved_requirements()
    revision = _payroll_revision()
    plan = isr_to_plan(revision)
    frontend = ReactFrontendBackend()
    frontend_repo = frontend.compile(plan)
    assert "src/App.tsx" in frontend_repo.files
    assert "payroll.gross" in plan.services[0].behavior.rules[0].rule_id
    assert any(node.type is NodeType.REQUIREMENT_REF for node in revision.graph.nodes.values())

    report = assess_payroll_readiness(
        requirements=requirements,
        isr=revision.graph,
        plan=plan,
        backend_capabilities=[
            BackendCapabilities(
                backend_id=backend.name,
                version=backend.version,
                supported_features=backend.supported_features,
            )
            for backend in (PythonFastAPIBackend(), RustAxumBackend())
        ],
        frontend_capabilities=BackendCapabilities(
            backend_id=frontend.name,
            version=frontend.version,
            supported_features=frontend.supported_features,
        ),
    )
    assert report.status == "NOT_CERTIFIED"
    assert report.mapped_requirement_count == 0
    assert report.unmapped_requirement_ids
    assert report.backend_gaps
    assert report.statutory_gaps
    assert report.evidence_gaps


def test_payroll_backend_compilers_fail_closed_on_unimplemented_semantics():
    plan = isr_to_plan(_payroll_revision())
    for backend in (PythonFastAPIBackend(), RustAxumBackend()):
        try:
            backend.compile(plan)
        except UnsupportedSemanticsError as exc:
            message = str(exc)
            if backend.name == "rust-axum":
                # The Rust backend still cannot emit declared operations or
                # enforce authorization policies.
                assert "api_contracts" in message
                assert "authorization_policies" in message
            else:
                # The Python backend emits declared operations and enforces
                # authorization for the policies it can bind to a route; the
                # payroll plan still fails closed on the semantics it does not
                # implement.
                assert "api_contracts" not in message
                assert "authorization_policies" not in message
        else:
            raise AssertionError(f"{backend.name} accepted unsupported payroll semantics")



def test_world_concern_tor_fixture_extracts_reviewable_candidates_not_approved_requirements():
    from pathlib import Path
    from reqgraph.ingestion.tor_extractor import ReviewStatus

    source = Path(__file__).resolve().parents[2] / "examples" / "payroll" / "world_concern_tor.md"
    draft = extract_tor_text(source.read_text(encoding="utf-8"), source.name)
    assert len(draft.candidates) >= 25
    assert all(candidate.status is ReviewStatus.NEEDS_REVIEW for candidate in draft.candidates)
    assert any("salary and benefits across multiple cost centers" in candidate.statement for candidate in draft.candidates)
    assert any("not later than 28 October 2026" in candidate.statement for candidate in draft.candidates)
