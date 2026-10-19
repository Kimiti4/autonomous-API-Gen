"""Behavioral backend emission contracts and fail-closed capability checks."""
from __future__ import annotations

import ast

from compiler.backends.python_fastapi import PythonFastAPIBackend
from compiler.backends.rust_axum import RustAxumBackend
from compiler.core.capabilities import (
    BackendCapabilities,
    SemanticFeature,
    UnsupportedSemanticsError,
    assert_plan_supported,
    required_features,
)
from compiler.core.lowering import isr_to_plan
from isr.core.graph import Edge, EdgeType, ISRGraph, Node, NodeType
from isr.core.identity import Provenance
from isr.core.revision import ISRRevision


def _revision() -> ISRRevision:
    nodes = {
        "service:payroll": Node(id="service:payroll", type=NodeType.SERVICE, properties={
            "label": "Payroll",
            "behavior": {
                "rules": [{
                    "rule_id": "payroll.gross",
                    "description": "Gross pay is salary plus allowances.",
                    "expression": {
                        "op": "add",
                        "args": [
                            {"op": "field", "field_ref": "Employee.base_salary"},
                            {"op": "field", "field_ref": "Employee.allowances"},
                        ],
                    },
                }],
                "transitions": [{
                    "transition_id": "payroll.submit",
                    "source_state": "draft",
                    "target_state": "submitted",
                    "guard": {
                        "op": "greater_than",
                        "args": [
                            {"op": "field", "field_ref": "Employee.base_salary"},
                            {"op": "literal", "value": 0},
                        ],
                    },
                }],
            },
        }),
        "data:employee": Node(id="data:employee", type=NodeType.DATA_MODEL, properties={
            "label": "Employee",
            "behavior": {"fields": [
                {"name": "employee_id", "value_type": "identifier"},
                {"name": "base_salary", "value_type": "money", "precision": 12, "scale": 2},
                {"name": "allowances", "value_type": "money", "precision": 12, "scale": 2},
            ]},
        }),
    }
    edges = {
        "persist": Edge(id="persist", type=EdgeType.PERSISTS, source_id="service:payroll", target_id="data:employee"),
    }
    return ISRRevision.create(
        "payroll-behavioral-emission",
        "rev-1",
        "1.0",
        ISRGraph(nodes=nodes, edges=edges),
        Provenance(created_by="behavioral-emission-test", created_at="2025-01-01T00:00:00Z"),
    )


def test_behavioral_features_are_explicit_and_supported_by_reference_backends():
    plan = isr_to_plan(_revision())
    required = required_features(plan)
    assert required == frozenset({
        SemanticFeature.TYPED_FIELDS,
        SemanticFeature.EXPRESSIONS,
        SemanticFeature.BUSINESS_RULES,
        SemanticFeature.STATE_TRANSITIONS,
    })
    for backend in (PythonFastAPIBackend(), RustAxumBackend()):
        assert_plan_supported(
            plan,
            BackendCapabilities(
                backend_id=backend.name,
                version=backend.version,
                supported_features=backend.supported_features,
            ),
        )


def test_python_emission_contains_executable_typed_fields_and_rule_methods():
    plan = isr_to_plan(_revision())
    repo = PythonFastAPIBackend().compile(plan)
    domain_source = repo.files["app/domain/Employee.py"]
    service_source = repo.files["app/application/Payroll.py"]
    behavior_source = repo.files["app/core/behavior.py"]
    tests_source = repo.files["tests/test_app.py"]

    # Syntax parse is an actual parser check, not a string-only smoke test.
    for path, source in repo.files.items():
        if path.endswith(".py"):
            ast.parse(source, filename=path)

    assert "base_salary: Decimal" in domain_source
    assert "def evaluate_rule" in service_source
    assert "def apply_transition" in service_source
    assert "def evaluate_expression" in behavior_source
    assert "def validate_fields" in behavior_source
    assert "def test_behavior_expression_arithmetic" in tests_source
    assert "def test_behavior_state_transition_checks_guard_and_source" in tests_source


def test_rust_emission_contains_compilable_module_shapes_and_behavior_tests():
    plan = isr_to_plan(_revision())
    repo = RustAxumBackend().compile(plan)
    domain_source = repo.files["src/domain/Employee.rs"]
    service_source = repo.files["src/application/Payroll.rs"]
    behavior_source = repo.files["src/core/behavior.rs"]
    assert "\n" in domain_source
    assert "\n" in service_source
    assert "pub fn evaluate_rule" in service_source
    assert "pub fn apply_transition" in service_source
    assert "pub fn validate_fields" in behavior_source
    assert "fn decimal_expression_uses_exact_decimal_arithmetic()" in behavior_source


def test_structural_only_backend_cannot_accept_behavioral_plan():
    plan = isr_to_plan(_revision())
    try:
        assert_plan_supported(
            plan,
            BackendCapabilities(backend_id="structural-only", version="0"),
        )
    except UnsupportedSemanticsError as exc:
        assert "typed_fields" in str(exc)
        assert "business_rules" in str(exc)
    else:
        raise AssertionError("unsupported behavior must not pass a structural-only backend")
