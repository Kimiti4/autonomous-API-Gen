from __future__ import annotations

from compiler.core.capabilities import BackendCapabilities
from compiler.core.plan import ApiOperation, CompilationPlan
from isr.core.behavior import ApiBehavior
from isr.core.graph import ISRGraph, Node, NodeType
from isr.core.identity import Provenance
from isr.core.revision import ISRRevision
from reqgraph.core.graph import Priority, RequirementGraph, RequirementKind, RequirementNode
from certification.payroll.certifier import certify_payroll_candidate


def _inputs():
    requirements = RequirementGraph(
        schema_version="1.0",
        nodes={
            "REQ-PAY-001": RequirementNode(
                id="REQ-PAY-001",
                kind=RequirementKind.FUNCTIONAL,
                statement="The system shall calculate gross pay.",
                priority=Priority.MUST,
                acceptance_criteria=("gross pay equals salary plus allowances",),
                source_refs=("tor#L1-L1",),
            )
        },
    )
    graph = ISRGraph(nodes={
        "requirement_ref:REQ-PAY-001": Node(
            id="requirement_ref:REQ-PAY-001",
            type=NodeType.REQUIREMENT_REF,
            properties={
                "ref_id": "REQ-PAY-001",
                "requirement_id": "REQ-PAY-001",
                "semantic_content": "The system shall calculate gross pay.",
                "statement": "The system shall calculate gross pay.",
            },
        )
    })
    revision = ISRRevision.create(
        system_id="payroll-system",
        revision_id="rev-1",
        schema_version="1.0",
        graph=graph,
        provenance=Provenance(
            created_by="payroll-certifier-test",
            created_at="2026-10-19T10:00:00Z",
            requirement_refs=("REQ-PAY-001",),
        ),
    )
    plan = CompilationPlan(
        plan_id=f"plan:{revision.content_hash[:16]}",
        isr_id=revision.system_id,
    )
    caps = {
        backend_id: BackendCapabilities(backend_id=backend_id, version="test")
        for backend_id in ("python-fastapi", "rust-axum")
    }
    return requirements, revision, plan, caps


def test_payroll_candidate_is_not_certified_without_behavioral_and_runtime_evidence():
    requirements, revision, plan, caps = _inputs()
    report = certify_payroll_candidate(
        requirement_graph=requirements,
        revision=revision,
        plan=plan,
        candidate_sha256="a" * 64,
        payroll_period_start="2026-10-01",
        payroll_period_end="2026-10-31",
        required_statutory_schemes=("income_tax", "social_security", "health_insurance"),
        required_oracle_categories=("gross_to_net", "statutory_deductions", "arrears_backpay", "cost_allocation"),
        backend_capabilities=caps,
        required_backends=("python-fastapi", "rust-axum"),
    )
    assert report.verdict == "NOT_CERTIFIED"
    assert not report.certified
    assert any("no typed data-model fields" in finding for finding in report.findings)
    assert any("missing statutory evidence" in finding for finding in report.findings)
    assert any("missing independent payroll oracle" in finding for finding in report.findings)
    assert any("missing real frontend" in finding for finding in report.findings)
    assert any("missing backend runtime evidence" in finding for finding in report.findings)


def test_payroll_certifier_rejects_malformed_candidate_hash():
    requirements, revision, plan, caps = _inputs()
    report = certify_payroll_candidate(
        requirement_graph=requirements,
        revision=revision,
        plan=plan,
        candidate_sha256="not-a-sha",
        payroll_period_start="2026-10-01",
        payroll_period_end="2026-10-31",
        required_statutory_schemes=(),
        required_oracle_categories=(),
        backend_capabilities=caps,
        required_backends=("python-fastapi", "rust-axum"),
    )
    assert report.verdict == "NOT_CERTIFIED"
    assert "candidate SHA-256 is missing or malformed" in report.findings


def test_payroll_certifier_rejects_backend_without_required_behavioral_capabilities():
    requirements, revision, plan, caps = _inputs()
    plan = CompilationPlan(
        plan_id=plan.plan_id,
        isr_id=plan.isr_id,
        apis=[ApiOperation(
            id="api:submit",
            name="submit",
            behavior=ApiBehavior(
                operation_id="payroll.submit",
                method="POST",
                path="/payroll-runs/submit",
            ),
        )],
    )
    report = certify_payroll_candidate(
        requirement_graph=requirements,
        revision=revision,
        plan=plan,
        candidate_sha256="a" * 64,
        payroll_period_start="2026-10-01",
        payroll_period_end="2026-10-31",
        required_statutory_schemes=(),
        required_oracle_categories=(),
        backend_capabilities=caps,
        required_backends=("python-fastapi", "rust-axum"),
    )
    assert any("missing API operation contracts" in finding for finding in report.findings)
    assert any("cannot implement this payroll plan" in finding for finding in report.findings)
