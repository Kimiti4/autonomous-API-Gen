"""Capability gate tests: unsupported semantics must never reach emitters."""
from __future__ import annotations

import json
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
from isr.core.behavior import (
    ApiBehavior,
    AuthorizationRule,
    ConsequenceBehavior,
    DataModelBehavior,
    EffectBehavior,
    Expression,
    SecurityBehavior,
)
from tests.support.execution_effect import (
    AUTHORIZED_OPERATION,
    PERMITTED_SIDE_EFFECT,
    executable_plan,
)


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


def test_consequence_contract_is_preserved_without_claiming_execution():
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
    assert SemanticFeature.CONSEQUENCE_PRESERVATION in required_features(plan)
    assert SemanticFeature.CONSEQUENCE_SEMANTICS not in required_features(plan)
    for backend in (PythonFastAPIBackend(), RustAxumBackend()):
        assert SemanticFeature.CONSEQUENCE_PRESERVATION in backend.supported_features
        repo = backend.compile(plan)
        manifest = json.loads(repo.files["docs/semantic-obligations.json"])
        assert manifest["consequences"][0]["behavior"]["outcome"] == "return prior result"
        assert manifest["consequences"][0]["related_node_ids"] == ["effect:create"]
        assert backend.conformance(plan, repo).passed
        tampered_files = dict(repo.files)
        manifest["consequences"][0]["behavior"]["outcome"] = "silently changed"
        tampered_files["docs/semantic-obligations.json"] = json.dumps(manifest)
        tampered_repo = repo.model_copy(update={"files": tampered_files})
        report = backend.conformance(plan, tampered_repo)
        assert not report.passed
        assert "semantic-obligations:mismatch" in report.missing


def test_source_declared_effect_policy_is_preserved_without_claiming_execution():
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
    assert SemanticFeature.EFFECT_POLICY_PRESERVATION in required_features(plan)
    assert SemanticFeature.EFFECT_SEMANTICS not in required_features(plan)
    for backend in (PythonFastAPIBackend(), RustAxumBackend()):
        repo = backend.compile(plan)
        manifest = json.loads(repo.files["docs/semantic-obligations.json"])
        assert manifest["effects"][0]["declared_policy"]["failure_policy"] == "rollback"


def test_executable_effect_contract_partial_fields_raise_error():
    """Setting only some execution contract fields raises ValueError."""
    with pytest.raises(ValueError):
        EffectBehavior(
            effect_kind="record",
            idempotent=True,
            idempotency_key_required=True,
            precondition=Expression(op="greater_than", args=(
                Expression(op="field", field_ref="amount"),
                Expression(op="literal", value=0),
            )),
        )


def test_executable_effect_contract_full_fields_ok():
    """All execution contract fields present with idempotent+key → valid."""
    beh = EffectBehavior(
        effect_kind="record",
        idempotent=True,
        idempotency_key_required=True,
        precondition=Expression(op="greater_than", args=(
            Expression(op="field", field_ref="amount"),
            Expression(op="literal", value=0),
        )),
        authorized_operation="payment.record",
        permitted_side_effect="payment_instruction",
        failure_behavior="reject_without_commit",
        postcondition=Expression(op="equal", args=(
            Expression(op="field", field_ref="approved"),
            Expression(op="literal", value=True),
        )),
    )
    assert beh.precondition.op == "greater_than"
    assert beh.authorized_operation == "payment.record"
    assert beh.permitted_side_effect == "payment_instruction"
    assert beh.failure_behavior == "reject_without_commit"
    assert beh.postcondition.op == "equal"


def test_full_executable_effect_contract_rejects_an_unsupported_failure_behavior():
    with pytest.raises(ValueError):
        EffectBehavior(
            effect_kind="record",
            idempotent=True,
            idempotency_key_required=True,
            precondition=Expression(op="greater_than", args=(
                Expression(op="field", field_ref="amount"),
                Expression(op="literal", value=0),
            )),
            authorized_operation="payment.create",
            permitted_side_effect="Payment",
            failure_behavior="retry_forever",  # only reject_without_commit is defined
            postcondition=Expression(op="equal", args=(
                Expression(op="field", field_ref="approved"),
                Expression(op="literal", value=True),
            )),
        )


def test_effect_execution_contract_claimed_by_python_only():
    """Plans with a bound, enforceable executable contract require EFFECT_EXECUTION."""
    plan = executable_plan()
    assert SemanticFeature.EFFECT_EXECUTION in required_features(plan)
    # Python supports the execution contract flag
    assert SemanticFeature.EFFECT_EXECUTION in PythonFastAPIBackend().supported_features
    # Rust does not yet advertise it
    assert SemanticFeature.EFFECT_EXECUTION not in RustAxumBackend().supported_features
    # Python should compile the plan (execution contract is supported)
    repo = PythonFastAPIBackend().compile(plan)
    effect_module = repo.files["app/effects/RecordPayment.py"]
    assert "apply_effect(EFFECT, idempotency_key, executor, ledger, context, principal, POLICIES)" in effect_module
    # Preservation is not execution: the declared contract is carried in the
    # manifest, while the runtime suite is what proves the behaviour.
    manifest = json.loads(repo.files["docs/semantic-obligations.json"])
    declared = manifest["effects"][0]["behavior"]
    assert declared["authorized_operation"] == AUTHORIZED_OPERATION
    assert declared["permitted_side_effect"] == PERMITTED_SIDE_EFFECT
    assert declared["failure_behavior"] == "reject_without_commit"
    assert declared["precondition"]["op"] == "greater_than"
    assert declared["postcondition"]["op"] == "equal"
    # Rust should raise UnsupportedSemanticsError with "effect_execution"
    with pytest.raises(UnsupportedSemanticsError, match="effect_execution"):
        RustAxumBackend().compile(plan)


def test_executable_effect_without_a_service_has_no_enforcement_point():
    plan = CompilationPlan(
        plan_id="unbound-exec-plan", isr_id="system",
        effects=[Effect(
            id="effect:record", name="Record",
            behavior=EffectBehavior(
                effect_kind="record",
                idempotent=True,
                idempotency_key_required=True,
                precondition=Expression(op="greater_than", args=(
                    Expression(op="field", field_ref="amount"),
                    Expression(op="literal", value=0),
                )),
                authorized_operation="payment.create",
                permitted_side_effect="Payment",
                failure_behavior="reject_without_commit",
                postcondition=Expression(op="equal", args=(
                    Expression(op="field", field_ref="approved"),
                    Expression(op="literal", value=True),
                )),
            ),
        )],
    )
    with pytest.raises(UnsupportedSemanticsError, match="exactly one service"):
        PythonFastAPIBackend().compile(plan)


def _replace_effect_property(name: str, value: object) -> CompilationPlan:
    plan = executable_plan()
    effect = plan.effects[0]
    behavior = effect.behavior.model_copy(update={name: value})
    service = plan.services[0]
    replaced_effect = Effect(
        id=effect.id, name=effect.name, behavior=behavior,
        declared_policy=effect.declared_policy,
    )
    replaced_service = Service(
        id=service.id,
        name=service.name,
        data_models=list(service.data_models),
        published_events=list(service.published_events),
        consumed_events=list(service.consumed_events),
        effects=[replaced_effect],
        behavior=service.behavior,
        security_policies=list(service.security_policies),
    )
    return CompilationPlan(
        plan_id=plan.plan_id,
        isr_id=plan.isr_id,
        services=[replaced_service],
        data_models=list(plan.data_models),
        security=list(plan.security),
        effects=[replaced_effect],
        effect_bindings=list(plan.effect_bindings),
    )


def test_executable_effect_must_name_a_route_the_service_emits():
    plan = _replace_effect_property("authorized_operation", "payment.approve")
    with pytest.raises(UnsupportedSemanticsError, match="does not emit"):
        PythonFastAPIBackend().compile(plan)


def test_executable_effect_side_effect_must_match_the_governed_resource():
    plan = _replace_effect_property("permitted_side_effect", "AuditLog")
    with pytest.raises(UnsupportedSemanticsError, match="governs 'Payment'"):
        PythonFastAPIBackend().compile(plan)


def test_executable_effect_requires_a_granting_allow_rule():
    plan = executable_plan()
    deny_only = SecurityPolicy(
        policy_id="security:clerk",
        behavior=SecurityBehavior(
            roles=("clerk",),
            rules=(AuthorizationRule(
                rule_id="deny-everything",
                effect="deny",
                roles=("clerk",),
                actions=(AUTHORIZED_OPERATION,),
                resource=PERMITTED_SIDE_EFFECT,
            ),),
        ),
    )
    service = plan.services[0]
    replaced_service = Service(
        id=service.id,
        name=service.name,
        data_models=list(service.data_models),
        effects=list(service.effects),
        behavior=service.behavior,
        security_policies=[deny_only],
    )
    broken = CompilationPlan(
        plan_id=plan.plan_id,
        isr_id=plan.isr_id,
        services=[replaced_service],
        data_models=list(plan.data_models),
        security=[deny_only],
        effects=list(plan.effects),
        effect_bindings=list(plan.effect_bindings),
    )
    with pytest.raises(UnsupportedSemanticsError, match="no principal could ever execute"):
        PythonFastAPIBackend().compile(broken)


def test_preservation_only_effect_still_requires_semantics():
    """Existing effect with only behavior fields (no execution) still requires
    EFFECT_SEMANTICS and fails on both backends — unchanged behavior."""
    effect = Effect(
        id="effect:transfer", name="transfer",
        behavior=EffectBehavior(
            effect_kind="bank_transfer",
            idempotent=True,
            idempotency_key_required=True,
        ),
    )
    plan = CompilationPlan(plan_id="pres-plan", isr_id="system", effects=[effect])
    assert SemanticFeature.EFFECT_SEMANTICS in required_features(plan)
    for backend in (PythonFastAPIBackend(), RustAxumBackend()):
        with pytest.raises(UnsupportedSemanticsError, match="effect_semantics"):
            backend.compile(plan)
