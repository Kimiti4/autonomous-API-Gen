"""Capability gate tests: unsupported semantics must never reach emitters."""
from __future__ import annotations

import pytest

from compiler.backends.python_fastapi import PythonFastAPIBackend
from compiler.backends.rust_axum import RustAxumBackend
from compiler.core.capabilities import (
    BackendCapabilities,
    SemanticFeature,
    UnsupportedSemanticsError,
    assert_plan_supported,
    required_features,
)
from compiler.core.plan import ApiOperation, CompilationPlan, Consequence, DataModel, Effect, SecurityPolicy, Service
from isr.core.behavior import ApiBehavior, ConsequenceBehavior, DataModelBehavior, EffectBehavior


def test_structural_plan_requires_no_behavioral_features():
    plan = CompilationPlan(plan_id="plan:1", isr_id="system:1")
    assert required_features(plan) == frozenset()
    assert_plan_supported(plan, BackendCapabilities(backend_id="test", version="1"))


def test_typed_fields_are_detected_as_a_required_capability():
    plan = CompilationPlan(
        plan_id="plan:2",
        isr_id="system:2",
        data_models=[DataModel(
            id="dm:employee",
            entity_name="Employee",
            behavior=DataModelBehavior.model_validate({
                "fields": [{"name": "salary", "value_type": "money", "precision": 12, "scale": 2, "constraints": [{"operator": "unique"}]}]
            }),
        )],
    )
    assert SemanticFeature.TYPED_FIELDS in required_features(plan)
    assert SemanticFeature.FIELD_CONSTRAINTS in required_features(plan)
    with pytest.raises(UnsupportedSemanticsError, match="field_constraints"):
        assert_plan_supported(plan, BackendCapabilities(backend_id="test", version="1"))


@pytest.mark.parametrize("backend", [PythonFastAPIBackend(), RustAxumBackend()])
def test_real_backend_compile_fails_closed_for_unimplemented_semantics(backend):
    plan = CompilationPlan(
        plan_id="plan:3",
        isr_id="system:3",
        data_models=[DataModel(
            id="dm:employee",
            entity_name="Employee",
            behavior=DataModelBehavior.model_validate({
                "fields": [{"name": "salary", "value_type": "money", "precision": 12, "scale": 2, "constraints": [{"operator": "unique"}]}]
            }),
        )],
    )
    with pytest.raises(UnsupportedSemanticsError, match="field_constraints"):
        backend.compile(plan)


def test_supported_behavioral_subset_is_emitted_by_both_backends():
    from compiler.core.plan import Service
    from isr.core.behavior import ServiceBehavior

    model = DataModel(
        id="dm:employee",
        entity_name="Employee",
        behavior=DataModelBehavior.model_validate({
            "fields": [{"name": "base_salary", "value_type": "money", "precision": 12, "scale": 2}]
        }),
    )
    service = Service(
        id="service:payroll",
        name="Payroll",
        data_models=[model],
        behavior=ServiceBehavior.model_validate({
            "rules": [{
                "rule_id": "gross-pay",
                "description": "Gross pay is base salary multiplied by one.",
                "expression": {"op": "multiply", "args": [
                    {"op": "field", "field_ref": "Employee.base_salary"},
                    {"op": "literal", "value": 1},
                ]},
            }],
            "transitions": [{
                "transition_id": "submit",
                "source_state": "draft",
                "target_state": "submitted",
            }],
        }),
    )
    plan = CompilationPlan(plan_id="plan:4", isr_id="system:4", services=[service], data_models=[model])
    assert SemanticFeature.BUSINESS_RULES in required_features(plan)
    assert SemanticFeature.STATE_TRANSITIONS in required_features(plan)
    for backend in (PythonFastAPIBackend(), RustAxumBackend()):
        repo = backend.compile(plan)
        assert repo.files
        if backend.name == "python-fastapi":
            assert "evaluate_rule" in repo.files["app/application/Payroll.py"]
            assert "def evaluate_expression" in repo.files["app/core/behavior.py"]
            assert "base_salary" in repo.files["app/domain/Employee.py"]
        else:
            assert "evaluate_rule" in repo.files["src/application/Payroll.rs"]
            assert "pub fn evaluate_expression" in repo.files["src/core/behavior.rs"]
            assert "base_salary" in repo.files["src/domain/Employee.rs"]


def test_api_contracts_are_claimed_only_where_operations_can_be_emitted():
    plan = CompilationPlan(
        plan_id="api-plan", isr_id="system",
        apis=[ApiOperation(
            id="api:submit", name="submit",
            behavior=ApiBehavior(operation_id="submit", method="POST", path="/submit"),
        )],
    )
    assert SemanticFeature.API_CONTRACTS in PythonFastAPIBackend().supported_features
    assert SemanticFeature.API_CONTRACTS not in RustAxumBackend().supported_features
    # Python claims the capability but this operation has no service binding, so
    # it fails closed rather than emitting an ownerless route.
    with pytest.raises(UnsupportedSemanticsError, match="EXPOSES"):
        PythonFastAPIBackend().compile(plan)
    with pytest.raises(UnsupportedSemanticsError, match="api_contracts"):
        RustAxumBackend().compile(plan)


def test_external_effect_semantics_remain_blocked_until_durable_execution_is_bound():
    effect = Effect(
        id="effect:transfer", name="transfer",
        behavior=EffectBehavior(
            effect_kind="bank_transfer", idempotent=True, idempotency_key_required=True
        ),
    )
    plan = CompilationPlan(plan_id="effect-plan", isr_id="system", effects=[effect])
    assert SemanticFeature.EFFECT_SEMANTICS in required_features(plan)
    for backend in (PythonFastAPIBackend(), RustAxumBackend()):
        with pytest.raises(UnsupportedSemanticsError, match="effect_semantics"):
            backend.compile(plan)


def test_legacy_structural_security_edge_does_not_claim_behavioral_auth():
    policy = SecurityPolicy(policy_id="security:legacy", behavior=None)
    service = Service(
        id="service:legacy",
        name="Legacy",
        security_policies=[policy],
    )
    plan = CompilationPlan(plan_id="legacy-plan", isr_id="legacy-system", services=[service], security=[policy])
    assert SemanticFeature.AUTHORIZATION_POLICIES not in required_features(plan)
    for backend in (PythonFastAPIBackend(), RustAxumBackend()):
        backend.compile(plan)


def test_operation_bound_untyped_policy_is_an_authorization_obligation():
    """A policy bound to an operation cannot vanish from capability checks.

    The obligation exists because the route is secured, not because the policy
    carries typed behavior. A backend that cannot prove enforcement must
    reject the candidate instead of emitting an unguarded route.
    """
    policy = SecurityPolicy(policy_id="security:payroll", behavior=None)
    plan = CompilationPlan(
        plan_id="secured-route-plan", isr_id="system",
        apis=[ApiOperation(id="api:submit", name="submit", security_policies=[policy])],
    )
    assert SemanticFeature.AUTHORIZATION_POLICIES in required_features(plan)
    for backend in (PythonFastAPIBackend(), RustAxumBackend()):
        with pytest.raises(UnsupportedSemanticsError, match="authorization_policies"):
            backend.compile(plan)


def test_policy_reference_without_typed_behavior_cannot_bypass_the_capability_gate():
    """A route that names a policy stays an obligation even if the policy is bare."""
    from compiler.core.authorization import assert_authorization_enforceable

    policy = SecurityPolicy(policy_id="security:payroll", behavior=None)
    plan = CompilationPlan(
        plan_id="referencing-route-plan", isr_id="system",
        apis=[ApiOperation(
            id="api:submit", name="submit",
            behavior=ApiBehavior(
                operation_id="submit", method="POST", path="/submit",
                authorization_policy_ids=("security:payroll",),
            ),
        )],
        security=[policy],
    )
    assert SemanticFeature.AUTHORIZATION_POLICIES in required_features(plan)
    # The obligation cannot be dropped: a backend that cannot enforce it must
    # refuse the plan, whether it refuses at the capability gate or at the
    # enforceability check.
    with pytest.raises(UnsupportedSemanticsError, match="authorization_policies"):
        assert_authorization_enforceable(plan)
    for backend in (PythonFastAPIBackend(), RustAxumBackend()):
        with pytest.raises(UnsupportedSemanticsError):
            backend.compile(plan)


def test_authentication_declaration_is_not_an_authorization_obligation():
    """A transport-level or structural declaration carries no rule to enforce.

    The certification corpus declares an authentication scheme per service.
    That declaration is not an authorization obligation, so it must not be
    reported as one, and it must not block the certified baseline.
    """
    policy = SecurityPolicy(policy_id="sec:policy", behavior=None)
    service = Service(
        id="service:orders", name="Orders",
        security_policies=[policy],
    )
    plan = CompilationPlan(
        plan_id="authn-declaration-plan", isr_id="system",
        services=[service], security=[policy],
    )
    assert SemanticFeature.AUTHORIZATION_POLICIES not in required_features(plan)
    for backend in (PythonFastAPIBackend(), RustAxumBackend()):
        backend.compile(plan)


def test_consequence_contract_is_an_explicit_unsupported_capability():
    plan = CompilationPlan(
        plan_id="consequence-plan", isr_id="system",
        consequences=[Consequence(
            id="consequence:duplicate",
            behavior=ConsequenceBehavior(
                trigger="duplicate request",
                outcome="return prior result",
                failure_policy="no duplicate side effect",
                effect_consequence={"effect_id": "effect:create", "retry_policy": "bounded"},
            ),
            related_node_ids=("effect:create",),
        )],
    )
    assert SemanticFeature.CONSEQUENCE_SEMANTICS in required_features(plan)
    for backend in (PythonFastAPIBackend(), RustAxumBackend()):
        assert SemanticFeature.CONSEQUENCE_SEMANTICS not in backend.supported_features
        with pytest.raises(UnsupportedSemanticsError, match="consequence_semantics"):
            backend.compile(plan)


def test_source_declared_effect_policy_cannot_bypass_capability_gate():
    plan = CompilationPlan(
        plan_id="legacy-effect-policy-plan", isr_id="system",
        effects=[Effect(
            id="effect:create", name="Create",
            declared_policy={
                "effect_type": "create",
                "idempotency_policy": "required",
                "replay_policy": "deduplicate",
                "failure_policy": "rollback",
            },
        )],
    )
    assert SemanticFeature.EFFECT_SEMANTICS in required_features(plan)
    for backend in (PythonFastAPIBackend(), RustAxumBackend()):
        with pytest.raises(UnsupportedSemanticsError, match="effect_semantics"):
            backend.compile(plan)
