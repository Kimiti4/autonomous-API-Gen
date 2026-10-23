"""Loss-aware ISR-to-plan projection tests."""
from __future__ import annotations

from compiler.core.lowering import isr_to_plan
from isr.core.behavior import BusinessRule
from isr.core.graph import Edge, EdgeType, ISRGraph, Node, NodeType
from isr.core.identity import Provenance
from isr.core.revision import ISRRevision


def _revision() -> ISRRevision:
    nodes = {
        "dm:employee": Node(id="dm:employee", type=NodeType.DATA_MODEL, properties={
            "label": "Employee",
            "behavior": {"fields": [
                {"name": "base_salary", "value_type": "money", "precision": 12, "scale": 2},
                {"name": "allowances", "value_type": "money", "precision": 12, "scale": 2},
            ]},
        }),
        "dm:orphan": Node(id="dm:orphan", type=NodeType.DATA_MODEL, properties={
            "label": "Standalone",
            "behavior": {"fields": [{"name": "reference", "value_type": "identifier"}]},
        }),
        "event:unlinked": Node(id="event:unlinked", type=NodeType.EVENT, properties={
            "label": "UnlinkedEvent",
            "behavior": {"fields": [{"name": "event_id", "value_type": "identifier"}]},
        }),
        "event:payroll-calculated": Node(id="event:payroll-calculated", type=NodeType.EVENT, properties={
            "label": "PayrollCalculated",
            "behavior": {"fields": [
                {"name": "payroll_run_id", "value_type": "identifier"},
                {"name": "gross_pay", "value_type": "money", "precision": 12, "scale": 2},
            ]},
        }),
        "security:payroll-approver": Node(id="security:payroll-approver", type=NodeType.SECURITY_POLICY, properties={
            "label": "PayrollApprover",
            "behavior": {"roles": ["payroll_approver"], "rules": [{
                "rule_id": "approve-payroll",
                "effect": "allow",
                "roles": ["payroll_approver"],
                "actions": ["payroll.approve"],
                "resource": "PayrollRun",
                "conditions": {"tenant_match": True},
            }]},
        }),
        "service:payroll": Node(id="service:payroll", type=NodeType.SERVICE, properties={
            "label": "Payroll",
            "behavior": {
                "rules": [{
                    "rule_id": "gross-pay",
                    "description": "Gross pay is base salary plus allowances.",
                    "expression": {"op": "add", "args": [
                        {"op": "field", "field_ref": "Employee.base_salary"},
                        {"op": "field", "field_ref": "Employee.allowances"},
                    ]},
                }],
                "transitions": [{
                    "transition_id": "submit-run",
                    "source_state": "draft",
                    "target_state": "submitted",
                    "guard": {"op": "greater_than", "args": [
                        {"op": "field", "field_ref": "Employee.base_salary"},
                        {"op": "literal", "value": 0},
                    ]},
                }],
            },
        }),
        "api:approve": Node(id="api:approve", type=NodeType.API, properties={
            "label": "approvePayroll",
            "behavior": {
                "operation_id": "payroll.approve",
                "method": "POST",
                "path": "/payroll-runs/{run_id}/approve",
                "request_fields": [{"name": "run_id", "value_type": "identifier"}],
                "response_fields": [{"name": "status", "value_type": "string"}],
                "authorization_policy_ids": ["security:payroll-approver"],
            },
        }),
        "effect:bank-transfer": Node(id="effect:bank-transfer", type=NodeType.EFFECT, properties={
            "label": "BankTransfer",
            "effect_type": "bank_transfer",
            "idempotency_policy": "required",
            "replay_policy": "deduplicate",
            "failure_policy": "rollback",
            "behavior": {"effect_kind": "bank_transfer", "idempotent": True, "idempotency_key_required": True},
        }),
        "invariant:nonnegative-pay": Node(id="invariant:nonnegative-pay", type=NodeType.INVARIANT, properties={
            "label": "NonnegativePay",
            "behavior": {
                "invariant_id": "nonnegative-pay",
                "description": "Base salary must be nonnegative.",
                "expression": {"op": "greater_or_equal", "args": [
                    {"op": "field", "field_ref": "Employee.base_salary"},
                    {"op": "literal", "value": 0},
                ]},
            },
        }),
        "consequence:duplicate": Node(id="consequence:duplicate", type=NodeType.CONSEQUENCE, properties={
            "label": "DuplicateRequest",
            "trigger": "duplicate request",
            "outcome": "return prior result",
            "failure_policy": "no duplicate side effect",
            "effect_consequence": {
                "effect_id": "effect:bank-transfer",
                "persistence": "dm:employee",
                "event": "none",
                "idempotency_key": "request-id",
                "retry_policy": "bounded",
            },
        }),
    }
    edges = {
        "e-persist": Edge(id="e-persist", type=EdgeType.PERSISTS, source_id="service:payroll", target_id="dm:employee"),
        "e-publish": Edge(id="e-publish", type=EdgeType.PUBLISHES, source_id="service:payroll", target_id="event:payroll-calculated"),
        "e-effect": Edge(id="e-effect", type=EdgeType.CAUSES_EFFECT, source_id="service:payroll", target_id="effect:bank-transfer"),
        "e-api-effect": Edge(id="e-api-effect", type=EdgeType.CAUSES_EFFECT, source_id="api:approve", target_id="effect:bank-transfer"),
        "e-consequence": Edge(id="e-consequence", type=EdgeType.CONSEQUENCE_OF, source_id="consequence:duplicate", target_id="effect:bank-transfer"),
        "e-secure-service": Edge(id="e-secure-service", type=EdgeType.SECURED_BY, source_id="service:payroll", target_id="security:payroll-approver"),
        "e-secure-api": Edge(id="e-secure-api", type=EdgeType.SECURED_BY, source_id="api:approve", target_id="security:payroll-approver"),
    }
    return ISRRevision.create(
        system_id="payroll-system",
        revision_id="rev-behavioral",
        schema_version="1.0",
        graph=ISRGraph(nodes=nodes, edges=edges),
        provenance=Provenance(created_by="projection-test", created_at="2025-01-01T00:00:00Z"),
    )


def test_projection_preserves_all_behavioral_contracts_and_security_bindings():
    revision = _revision()
    plan = isr_to_plan(revision)

    employee = next(model for service in plan.services for model in service.data_models)
    assert next(model for model in plan.data_models if model.id == "dm:orphan").behavior.fields[0].name == "reference"
    assert next(event for event in plan.events if event.id == "event:unlinked").behavior.fields[0].name == "event_id"
    assert [field.name for field in employee.behavior.fields] == ["base_salary", "allowances"]

    service = next(service for service in plan.services if service.id == "service:payroll")
    rule = service.behavior.rules[0]
    assert rule.model_dump(mode="json") == BusinessRule.model_validate(revision.graph.nodes["service:payroll"].properties["behavior"]["rules"][0]).model_dump(mode="json")
    assert rule.expression.args[0].field_ref == "Employee.base_salary"
    assert service.behavior.transitions[0].guard.args[0].field_ref == "Employee.base_salary"
    assert service.security_policies[0].policy_id == "security:payroll-approver"

    event = next(event for event in service.published_events if event.id == "event:payroll-calculated")
    assert [field.name for field in event.behavior.fields] == ["payroll_run_id", "gross_pay"]

    api = next(api for api in plan.apis if api.id == "api:approve")
    assert api.behavior.method == "POST"
    assert api.behavior.path == "/payroll-runs/{run_id}/approve"
    assert api.behavior.request_fields[0].name == "run_id"
    assert api.behavior.authorization_policy_ids == ("security:payroll-approver",)
    assert api.security_policies[0].behavior.rules[0].rule_id == "approve-payroll"

    effect = next(effect for effect in plan.effects if effect.id == "effect:bank-transfer")
    assert effect.behavior.effect_kind == "bank_transfer"
    assert effect.behavior.idempotent is True
    assert effect.behavior.idempotency_key_required is True
    assert effect.declared_policy == {
        "effect_type": "bank_transfer",
        "idempotency_policy": "required",
        "replay_policy": "deduplicate",
        "failure_policy": "rollback",
    }
    assert {(binding.edge_id, binding.source_id, binding.effect_id) for binding in plan.effect_bindings} == {
        ("e-effect", "service:payroll", "effect:bank-transfer"),
        ("e-api-effect", "api:approve", "effect:bank-transfer"),
    }

    consequence = next(item for item in plan.consequences if item.id == "consequence:duplicate")
    assert consequence.behavior.trigger == "duplicate request"
    assert consequence.behavior.outcome == "return prior result"
    assert consequence.behavior.failure_policy == "no duplicate side effect"
    assert consequence.behavior.effect_consequence["idempotency_key"] == "request-id"
    assert consequence.related_node_ids == ("effect:bank-transfer",)

    invariant = next(item for item in plan.invariants if item.id == "invariant:nonnegative-pay")
    assert invariant.behavior.expression.op == "greater_or_equal"
    assert invariant.behavior.expression.args[0].field_ref == "Employee.base_salary"


def test_projection_is_deterministic_for_same_content_revision():
    revision = _revision()
    first = isr_to_plan(revision).model_dump(mode="json")
    second = isr_to_plan(revision).model_dump(mode="json")
    assert first == second



def test_behavioral_plan_does_not_cross_backend_gate_with_unimplemented_api_effect_or_authz():
    from compiler.core.capabilities import (
        BackendCapabilities,
        SemanticFeature,
        UnsupportedSemanticsError,
        assert_plan_supported,
        required_features,
    )
    from compiler.backends.python_fastapi import PythonFastAPIBackend
    from compiler.backends.rust_axum import RustAxumBackend

    plan = isr_to_plan(_revision())
    required = required_features(plan)
    assert SemanticFeature.API_CONTRACTS in required
    assert SemanticFeature.AUTHORIZATION_POLICIES in required
    assert SemanticFeature.EFFECT_SEMANTICS in required
    assert SemanticFeature.CONSEQUENCE_PRESERVATION in required
    assert SemanticFeature.CONSEQUENCE_SEMANTICS not in required
    assert SemanticFeature.INVARIANTS in required

    for backend in (PythonFastAPIBackend(), RustAxumBackend()):
        try:
            assert_plan_supported(
                plan,
                BackendCapabilities(
                    backend_id=backend.name,
                    version=backend.version,
                    supported_features=backend.supported_features,
                ),
            )
        except UnsupportedSemanticsError as exc:
            message = str(exc)
            assert "effect_semantics" in message
            if backend.name == "rust-axum":
                # The Rust backend still cannot emit declared operations or
                # enforce authorization policies.
                assert "api_contracts" in message
                assert "authorization_policies" in message
            else:
                # The Python backend emits declared operations and enforces
                # authorization; the remaining blockers are the semantics it
                # still does not emit.
                assert "api_contracts" not in message
                assert "authorization_policies" not in message
        else:
            raise AssertionError(f"{backend.name} accepted unsupported semantic obligations")


def test_consequence_without_explicit_effect_or_invariant_binding_is_rejected():
    revision = _revision()
    edges = {
        edge_id: edge for edge_id, edge in revision.graph.edges.items()
        if edge.type != EdgeType.CONSEQUENCE_OF
    }
    broken_graph = ISRGraph(nodes=revision.graph.nodes, edges=edges)
    broken = ISRRevision.create(
        system_id=revision.system_id,
        revision_id="rev-missing-consequence-binding",
        schema_version=revision.schema_version,
        graph=broken_graph,
        provenance=revision.provenance,
    )
    import pytest
    with pytest.raises(ValueError, match="no explicit CONSEQUENCE_OF binding"):
        isr_to_plan(broken)
