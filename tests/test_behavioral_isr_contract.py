"""Contract tests for typed, technology-neutral ISR behavioral semantics."""
from __future__ import annotations

import pytest
from pydantic import ValidationError

from isr.core.behavior import (
    ApiBehavior,
    DataModelBehavior,
    EffectBehavior,
    Expression,
    SecurityBehavior,
    ServiceBehavior,
    ValueType,
    expression_field_refs,
)
from isr.core.behavior_validation import BehavioralContractViolation
from isr.core.graph import Edge, EdgeType, ISRGraph, Node, NodeType
from isr.core.identity import Provenance, compute_content_hash
from isr.core.revision import ISRRevision


def _field(name: str, value_type: ValueType = ValueType.STRING, **kwargs) -> dict:
    return {"name": name, "value_type": value_type.value, **kwargs}


def _provenance() -> Provenance:
    return Provenance(created_by="behavior-contract-test", created_at="2025-01-01T00:00:00Z")


def _revision(graph: ISRGraph) -> ISRRevision:
    return ISRRevision.create("behavior-test", "rev-1", "1.0", graph, _provenance())


def test_data_model_behavior_requires_typed_fields():
    spec = DataModelBehavior.model_validate({
        "fields": [
            _field("employee_id", ValueType.IDENTIFIER),
            _field("gross_pay", ValueType.MONEY, precision=12, scale=2),
        ]
    })
    assert [field.name for field in spec.fields] == ["employee_id", "gross_pay"]


@pytest.mark.parametrize("payload", [
    {"fields": [{"name": "bad-name", "value_type": "string"}]},
    {"fields": [{"name": "amount", "value_type": "money", "precision": 4, "scale": 5}]},
    {"fields": [{"name": "amount", "value_type": "string", "precision": 4}]},
    {"fields": [{"name": "amount", "value_type": "integer", "required": True, "nullable": True}]},
])
def test_invalid_field_shapes_fail_closed(payload):
    with pytest.raises(ValidationError):
        DataModelBehavior.model_validate(payload)


def test_expression_is_a_bounded_ast_not_executable_source():
    expr = Expression.model_validate({
        "op": "multiply",
        "args": [
            {"op": "field", "field_ref": "hours"},
            {"op": "field", "field_ref": "hourly_rate"},
        ],
    })
    assert expression_field_refs(expr) == {"hours", "hourly_rate"}
    with pytest.raises(ValidationError):
        Expression.model_validate({"op": "__import__", "value": "os"})


def test_expression_arity_is_enforced():
    with pytest.raises(ValidationError):
        Expression.model_validate({"op": "divide", "args": [{"op": "literal", "value": 1}]})


def test_service_rules_and_transitions_are_typed():
    behavior = ServiceBehavior.model_validate({
        "rules": [{
            "rule_id": "payroll.gross",
            "description": "Gross pay is base salary plus allowances.",
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
        }],
    })
    assert behavior.rules[0].rule_id == "payroll.gross"
    assert behavior.transitions[0].target_state == "submitted"


def test_api_contract_is_framework_neutral_and_explicit():
    api = ApiBehavior.model_validate({
        "operation_id": "payroll.submit",
        "method": "POST",
        "path": "/payroll-runs/{run_id}/submit",
        "authorization_policy_ids": ["payroll-approver"],
    })
    assert api.method == "POST"
    assert api.authorization_policy_ids == ("payroll-approver",)


def test_effect_idempotency_contract_cannot_contradict_itself():
    with pytest.raises(ValidationError):
        EffectBehavior.model_validate({
            "effect_kind": "bank_transfer",
            "idempotent": False,
            "idempotency_key_required": True,
        })


def test_security_policy_rejects_undeclared_roles():
    with pytest.raises(ValidationError):
        SecurityBehavior.model_validate({
            "roles": ["payroll_admin"],
            "rules": [{
                "rule_id": "bad-role",
                "effect": "allow",
                "roles": ["everyone"],
                "actions": ["payroll.read"],
                "resource": "PayrollRun",
            }],
        })


def test_revision_rejects_duplicate_fields_and_unknown_expression_refs():
    graph = ISRGraph(nodes={
        "dm:employee": Node(id="dm:employee", type=NodeType.DATA_MODEL, properties={
            "label": "Employee",
            "behavior": {"fields": [
                _field("salary", ValueType.MONEY, precision=12, scale=2),
                _field("salary", ValueType.MONEY, precision=12, scale=2),
            ]},
        }),
    })
    with pytest.raises(BehavioralContractViolation, match="Duplicate field names"):
        _revision(graph)

    graph = ISRGraph(nodes={
        "dm:employee": Node(id="dm:employee", type=NodeType.DATA_MODEL, properties={
            "label": "Employee",
            "behavior": {"fields": [_field("salary", ValueType.MONEY, precision=12, scale=2)]},
        }),
        "service:payroll": Node(id="service:payroll", type=NodeType.SERVICE, properties={
            "behavior": {"rules": [{
                "rule_id": "payroll.gross",
                "description": "Gross pay formula.",
                "expression": {"op": "field", "field_ref": "Employee.missing"},
            }]},
        }),
    })
    with pytest.raises(BehavioralContractViolation, match="unknown or ambiguous fields"):
        _revision(graph)


def test_revision_rejects_missing_policy_binding():
    graph = ISRGraph(nodes={
        "api:submit": Node(id="api:submit", type=NodeType.API, properties={
            "behavior": {
                "operation_id": "payroll.submit",
                "method": "POST",
                "path": "/payroll-runs",
                "authorization_policy_ids": ["missing-policy"],
            },
        }),
    })
    with pytest.raises(BehavioralContractViolation, match="missing authorization policies"):
        _revision(graph)


def test_behavior_payload_is_content_addressed_and_legacy_hash_unchanged():
    legacy = ISRGraph(nodes={
        "service:payroll": Node(id="service:payroll", type=NodeType.SERVICE, properties={"label": "payroll"}),
    })
    rev = _revision(legacy)
    assert rev.content_hash == compute_content_hash("1.0", legacy)

    behavioral = ISRGraph(nodes={
        "dm:employee": Node(id="dm:employee", type=NodeType.DATA_MODEL, properties={
            "label": "Employee",
            "behavior": {"fields": [_field("salary", ValueType.MONEY, precision=12, scale=2)]},
        }),
    })
    first = _revision(behavioral)
    changed = ISRGraph(nodes={
        "dm:employee": Node(id="dm:employee", type=NodeType.DATA_MODEL, properties={
            "label": "Employee",
            "behavior": {"fields": [_field("salary", ValueType.MONEY, precision=13, scale=2)]},
        }),
    })
    second = _revision(changed)
    assert first.content_hash != second.content_hash


def test_behavior_payload_on_unsupported_node_type_fails_closed():
    graph = ISRGraph(nodes={
        "event:payroll": Node(id="event:payroll", type=NodeType.EVENT, properties={
            "behavior": {"effect_kind": "bank_transfer"},
        }),
    })
    with pytest.raises(BehavioralContractViolation, match="not supported"):
        _revision(graph)
