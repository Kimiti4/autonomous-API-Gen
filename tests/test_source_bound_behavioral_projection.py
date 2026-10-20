"""Source TOR -> typed behavioral ISR -> plan -> certified emitter evidence."""
from __future__ import annotations

import hashlib

import pytest

from compiler.backends.python_fastapi import PythonFastAPIBackend
from compiler.backends.react_frontend import ReactFrontendBackend
from compiler.backends.rust_axum import RustAxumBackend
from compiler.core.lowering import isr_to_plan
from reqgraph.adapters.tor_isr import (
    project_tor_to_isr,
    requirement_graph_hash,
    traceability_record,
)
from reqgraph.ingestion.tor_extractor import HumanApproval, extract_tor_text
from tests.support.tor_sources import (
    backend_plan,
    backend_projection,
    full_stack_plan,
    full_stack_projection,
)


def test_reviewed_tor_projects_typed_behavior_and_full_source_provenance():
    projection = full_stack_projection()
    graph = projection.revision.graph
    requirements = projection.requirement_graph

    assert all(
        node.properties["source_sha256"] == projection.source_sha256
        for node in requirements.nodes.values()
    )
    assert set(projection.revision.provenance.requirement_refs) == set(requirements.nodes)
    for requirement_id in requirements.nodes:
        assert f"requirement_ref:{requirement_id}" in graph.nodes
    assert graph.nodes["data:employee"].properties["behavior"]["fields"][1]["name"] == "base_salary"
    assert graph.nodes["service:payroll"].properties["behavior"]["rules"][0]["rule_id"] == "payroll.gross"
    assert graph.nodes["api:payroll"].properties["behavior"]["operation_id"] == "payroll.submit"
    assert graph.nodes["ui:payroll"].properties["behavior"]["title"] == "Payroll Management"


def test_plan_preserves_typed_behavior_and_traceability_record_binds_every_stage():
    projection = full_stack_projection()
    plan = full_stack_plan()

    assert plan.data_models[0].behavior.fields[1].name == "base_salary"
    assert plan.services[0].data_models[0].id == "data:employee"
    assert plan.services[0].behavior.rules[0].expression.args[0].field_ref == "Employee.base_salary"
    assert plan.services[0].behavior.transitions[0].transition_id == "payroll.submit"
    assert plan.apis[0].behavior.method == "POST"
    assert [field.name for field in plan.apis[0].behavior.request_fields] == [
        "employee_id", "base_salary", "allowances",
    ]
    assert plan.frontend_routes[0].behavior.path == "/payroll"
    assert plan.frontend_routes[0].interactions[0].behavior.action == "submit"
    assert (
        plan.frontend_routes[0].interactions[0].target_api_operation.behavior.operation_id
        == "payroll.submit"
    )
    assert plan.plan_id == f"plan:{projection.revision.content_hash[:16]}"

    record = traceability_record(projection, plan_id=plan.plan_id)
    assert record.source_name == "payroll-tor.md"
    assert record.source_sha256 == projection.source_sha256
    assert record.requirement_graph_hash == requirement_graph_hash(projection.requirement_graph)
    assert record.requirement_ids == tuple(sorted(projection.requirement_graph.nodes))
    assert record.isr_content_hash == projection.revision.content_hash
    assert record.isr_node_ids == (
        "api:payroll", "data:employee", "service:payroll", "ui:payroll", "ui:submit-payroll",
    )
    assert record.isr_edge_ids == (
        "persist:employee", "ui-contains-interaction", "ui-invokes-api", "ui-routes-api",
    )


def _money_precision_projection(precision: int):
    draft = extract_tor_text(
        "FUNCTIONAL REQUIREMENTS\n- The system shall manage employee payroll records.",
        "mutation-tor.md",
    )
    item = draft.candidates[0]
    approval = HumanApproval(
        reviewer_id="reviewer",
        approval_ref="decision:1",
        acceptance_criteria=("A test verifies it.",),
        isr_nodes=(
            {
                "id": "data:employee",
                "type": "data_model",
                "properties": {
                    "label": "Employee",
                    "behavior": {"fields": [
                        {"name": "employee_id", "value_type": "identifier"},
                        {"name": "base_salary", "value_type": "money",
                         "precision": precision, "scale": 2},
                    ]},
                    "source_requirement_ids": [item.requirement_id],
                },
            },
            {
                "id": "service:payroll",
                "type": "service",
                "properties": {
                    "label": "Payroll",
                    "source_requirement_ids": [item.requirement_id],
                },
            },
        ),
        isr_edges=({
            "id": "persist:employee",
            "type": "persists",
            "source_id": "service:payroll",
            "target_id": "data:employee",
            "properties": {"source_requirement_ids": [item.requirement_id]},
        },),
    )
    return project_tor_to_isr(
        draft,
        {item.requirement_id: approval},
        system_id="mutation-source",
        revision_id=f"rev-mutation-{precision}",
        created_at="2026-01-01T00:00:00Z",
    )


def test_reviewed_behavior_mutation_changes_the_plan_and_emitted_code():
    first = _money_precision_projection(12)
    second = _money_precision_projection(14)
    first_plan = isr_to_plan(first.revision)
    second_plan = isr_to_plan(second.revision)
    assert first_plan.plan_id != second_plan.plan_id

    first_code = PythonFastAPIBackend().compile(first_plan).files["app/domain/Employee.py"]
    second_code = PythonFastAPIBackend().compile(second_plan).files["app/domain/Employee.py"]
    assert "max_digits=12" in first_code
    assert "max_digits=14" in second_code
    assert first_code != second_code


def test_source_mutation_invalidates_reviewed_projection():
    projection = backend_projection()
    draft = extract_tor_text(
        "FUNCTIONAL REQUIREMENTS\n- The system shall manage employees.", "a.md"
    )
    item = draft.candidates[0]
    approvals = {
        item.requirement_id: HumanApproval(
            reviewer_id="reviewer",
            approval_ref="decision:1",
            acceptance_criteria=("A test verifies it.",),
            isr_nodes=({
                "id": "data:employee",
                "type": "data_model",
                "properties": {
                    "label": "Employee",
                    "behavior": {"fields": [{"name": "employee_id", "value_type": "identifier"}]},
                    "source_requirement_ids": [item.requirement_id],
                },
            },),
        ),
    }
    changed = draft.model_copy(update={"source_text": draft.source_text + "\nchanged"})
    with pytest.raises(ValueError, match="source changed"):
        project_tor_to_isr(
            changed,
            approvals,
            system_id="mutated",
            revision_id="rev-mutated",
            created_at="2026-01-01T00:00:00Z",
        )
    assert projection.source_sha256 != hashlib.sha256(
        changed.source_text.encode("utf-8")
    ).hexdigest()


def test_approved_requirement_without_an_explicit_declaration_blocks_projection():
    draft = extract_tor_text(
        "FUNCTIONAL REQUIREMENTS\n- The system shall manage employees.\n- The system shall audit employees.",
        "unmapped-tor.md",
    )
    first, second = draft.candidates
    node = {
        "id": "data:employee",
        "type": "data_model",
        "properties": {
            "label": "Employee",
            "behavior": {"fields": [{"name": "employee_id", "value_type": "identifier"}]},
            "source_requirement_ids": [first.requirement_id],
        },
    }
    approvals = {
        first.requirement_id: HumanApproval(
            reviewer_id="reviewer", approval_ref="decision:1",
            acceptance_criteria=("A test verifies it.",), isr_nodes=(node,),
        ),
        second.requirement_id: HumanApproval(
            reviewer_id="reviewer", approval_ref="decision:2",
            acceptance_criteria=("A test verifies it.",),
        ),
    }
    with pytest.raises(ValueError, match="no explicit ISR declaration"):
        project_tor_to_isr(
            draft,
            approvals,
            system_id="unmapped",
            revision_id="rev-unmapped",
            created_at="2026-01-01T00:00:00Z",
        )


def test_declarations_must_bind_to_approved_requirement_ids():
    draft = extract_tor_text("FUNCTIONAL REQUIREMENTS\n- The system shall manage employees.", "a.md")
    item = draft.candidates[0]
    approval = HumanApproval(
        reviewer_id="reviewer",
        approval_ref="decision:1",
        acceptance_criteria=("A test verifies it.",),
        isr_nodes=({
            "id": "data:employee",
            "type": "data_model",
            "properties": {
                "label": "Employee",
                "behavior": {"fields": [{"name": "employee_id", "value_type": "identifier"}]},
                "source_requirement_ids": ["invented-requirement"],
            },
        },),
    )
    with pytest.raises(ValueError, match="unknown source requirement IDs"):
        draft.approve({item.requirement_id: approval})


def test_declaration_ids_are_unique_across_reviewed_requirements():
    draft = extract_tor_text(
        "FUNCTIONAL REQUIREMENTS\n- The system shall manage employees.\n- The system shall audit employees.",
        "a.md",
    )
    first, second = draft.candidates
    node = {
        "id": "data:employee",
        "type": "data_model",
        "properties": {
            "label": "Employee",
            "behavior": {"fields": [{"name": "employee_id", "value_type": "identifier"}]},
            "source_requirement_ids": [first.requirement_id],
        },
    }
    duplicate = {
        **node,
        "properties": {
            **node["properties"],
            "source_requirement_ids": [second.requirement_id],
        },
    }
    approvals = {
        first.requirement_id: HumanApproval(
            reviewer_id="reviewer", approval_ref="decision:1",
            acceptance_criteria=("A test verifies it.",), isr_nodes=(node,),
        ),
        second.requirement_id: HumanApproval(
            reviewer_id="reviewer", approval_ref="decision:2",
            acceptance_criteria=("A test verifies it.",), isr_nodes=(duplicate,),
        ),
    }
    with pytest.raises(ValueError, match="duplicate ISR node declaration"):
        draft.approve(approvals)


def test_certified_emitters_consume_the_source_derived_behavior():
    backend = backend_plan()
    python_repo = PythonFastAPIBackend().compile(backend)
    rust_repo = RustAxumBackend().compile(backend)
    frontend_repo = ReactFrontendBackend().compile(full_stack_plan())

    assert "base_salary: Decimal" in python_repo.files["app/domain/Employee.py"]
    assert "def test_generated_rule_payroll_gross" in python_repo.files["tests/test_app.py"]
    assert "pub fn evaluate_rule" in rust_repo.files["src/application/Payroll.rs"]
    assert "base_salary" in rust_repo.files["src/domain/Employee.rs"]
    assert "Payroll Management" in frontend_repo.files["src/App.tsx"]
    assert "/payroll-runs" in frontend_repo.files["src/App.tsx"]
    assert "calls the declared API" in frontend_repo.files["src/App.test.tsx"]
