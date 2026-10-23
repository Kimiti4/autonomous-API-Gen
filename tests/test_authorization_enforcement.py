"""Stage 2 authorization enforcement: trusted principal and per-route binding.

These tests are the compiler-side contract for the enforcement increment. The
runtime behaviour itself is proven by the generated application's own suite,
which the integration test executes.
"""
from __future__ import annotations

import ast

import pytest

from compiler.backends.python_fastapi import PythonFastAPIBackend
from compiler.backends.rust_axum import RustAxumBackend
from compiler.core.authorization import (
    assert_authorization_enforceable,
    canonical_action,
    protected_services,
)
from compiler.core.capabilities import SemanticFeature, UnsupportedSemanticsError
from compiler.core.plan import ApiOperation, CompilationPlan, SecurityPolicy, Service
from isr.core.behavior import ApiBehavior
from isr.core.graph import Edge, EdgeType
from compiler.core.lowering import isr_to_plan
from tests.support.tor_sources import (
    authorized_backend_plan,
    backend_plan,
    full_stack_projection,
)


def _emitted(plan) -> dict[str, str]:
    return PythonFastAPIBackend().compile(plan).files


def test_source_bound_policy_reaches_the_emitted_route():
    plan = authorized_backend_plan()
    protected = protected_services(plan)
    assert "service:payroll" in protected
    main = _emitted(plan)["app/main.py"]
    assert 'action="employee.read"' in main
    assert 'resource="Employee"' in main
    assert "SERVICE_POLICIES" in main


def test_each_emitted_route_is_bound_to_its_own_action():
    main = _emitted(authorized_backend_plan())["app/main.py"]
    for verb in ("read", "create", "update", "delete"):
        assert f'action="{canonical_action("Employee", verb)}"' in main


def test_generated_runtime_resolves_identity_only_from_a_signed_token():
    source = _emitted(authorized_backend_plan())["app/core/authorization.py"]
    lowered = source.lower()
    # Roles and tenant identity come from verified claims, never from headers.
    assert "x-role" not in lowered
    assert "x-tenant" not in lowered
    assert "x-forwarded-user" not in lowered
    assert 'request.headers.get("authorization")' in source
    assert "hmac.compare_digest" in source
    assert "GENERATED_AUTH_SECRET" in source


def test_generated_runtime_denies_by_default_and_explicit_deny_wins():
    source = _emitted(authorized_backend_plan())["app/core/authorization.py"]
    assert "no matching allow rule; default deny" in source
    assert source.index("explicit deny rule") < source.index("allow rule '")
    assert "tenant identity is missing" in source
    assert "different tenant" in source
    # Absence of a required attribute must never grant access.
    assert "never grants access" in source


def test_generated_suite_proves_allow_deny_and_no_mutation_after_denial():
    source = _emitted(authorized_backend_plan())["tests/test_app.py"]
    for name in (
        "test_authorization_requires_a_signed_token",
        "test_authorization_rejects_a_tampered_token",
        "test_authorization_denies_a_principal_without_a_grant",
        "test_denied_request_does_not_mutate_state",
        "test_authorization_runtime_denies_by_default",
        "test_authorization_runtime_explicit_deny_wins_over_allow",
        "test_authorization_runtime_missing_attribute_never_grants",
        "test_authorization_runtime_isolates_tenants",
    ):
        assert f"def {name}():" in source


def test_changing_the_policy_changes_the_emitted_enforcement():
    plan = authorized_backend_plan()
    policies = _emitted(plan)["app/core/policies.py"]
    assert "payroll_approver" in policies

    policy = next(p for p in plan.security if p.policy_id == "security:payroll-approver")
    changed = policy.model_copy(update={
        "behavior": policy.behavior.model_copy(update={
            "roles": ("payroll_admin",),
            "rules": tuple(
                rule.model_copy(update={"roles": ("payroll_admin",)})
                for rule in policy.behavior.rules
            ),
        }),
    })
    revised = plan.model_copy(update={
        "security": [changed],
        "services": [
            service.model_copy(update={
                "security_policies": [
                    changed if item.policy_id == changed.policy_id else item
                    for item in service.security_policies
                ],
            })
            for service in plan.services
        ],
    })
    revised_policies = _emitted(revised)["app/core/policies.py"]
    assert "payroll_admin" in revised_policies
    assert "payroll_approver" not in revised_policies


def test_operation_bound_obligation_fails_closed():
    policy = SecurityPolicy(policy_id="security:payroll", behavior=None)
    plan = CompilationPlan(
        plan_id="operation-plan", isr_id="system",
        apis=[ApiOperation(
            id="api:submit", name="submit",
            behavior=ApiBehavior(
                operation_id="submit", method="POST", path="/submit",
                authorization_policy_ids=("security:payroll",),
            ),
        )],
        security=[policy],
    )
    with pytest.raises(UnsupportedSemanticsError, match="authorization_policies"):
        assert_authorization_enforceable(plan)
    for backend in (PythonFastAPIBackend(), RustAxumBackend()):
        with pytest.raises(UnsupportedSemanticsError):
            backend.compile(plan)


def test_rule_naming_an_action_that_is_not_a_route_fails_closed():
    plan = authorized_backend_plan()
    policy = next(p for p in plan.security if p.policy_id == "security:payroll-approver")
    rule = policy.behavior.rules[0]
    broken = policy.model_copy(update={
        "behavior": policy.behavior.model_copy(update={
            "rules": (rule.model_copy(update={"actions": ("payroll.submit",)}),),
        }),
    })
    broken_plan = plan.model_copy(update={
        "security": [broken],
        "services": [
            service.model_copy(update={
                "security_policies": [
                    broken if item.policy_id == broken.policy_id else item
                    for item in service.security_policies
                ],
            })
            for service in plan.services
        ],
    })
    with pytest.raises(UnsupportedSemanticsError, match="payroll.submit"):
        assert_authorization_enforceable(broken_plan)


def test_only_the_python_backend_claims_authorization_support():
    assert SemanticFeature.AUTHORIZATION_POLICIES in PythonFastAPIBackend().supported_features
    assert SemanticFeature.AUTHORIZATION_POLICIES not in RustAxumBackend().supported_features


def test_declaration_only_policy_leaves_routes_unprotected():
    plan = backend_plan()
    main = _emitted(plan)["app/main.py"]
    assert "require_authorization" not in main
    assert "SERVICE_POLICIES" not in main


def test_emitted_sources_are_valid_python():
    for path, source in _emitted(authorized_backend_plan()).items():
        if path.endswith(".py"):
            ast.parse(source, filename=path)



def test_lowering_preserves_explicit_service_exposes_api_binding():
    revision = full_stack_projection().revision
    graph = revision.graph
    edges = dict(graph.edges)
    edges["exposes:payroll"] = Edge(
        id="exposes:payroll",
        type=EdgeType.EXPOSES,
        source_id="service:payroll",
        target_id="api:payroll",
    )
    bound_revision = revision.model_copy(
        update={"graph": graph.model_copy(update={"edges": edges})}
    )

    plan = isr_to_plan(bound_revision)
    operation = next(api for api in plan.apis if api.id == "api:payroll")
    assert operation.service_id == "service:payroll"


def test_lowering_does_not_infer_api_service_from_names_or_fields():
    plan = isr_to_plan(full_stack_projection().revision)
    operation = next(api for api in plan.apis if api.id == "api:payroll")
    assert operation.service_id is None


def test_lowering_rejects_ambiguous_service_exposes_api_bindings():
    revision = full_stack_projection().revision
    graph = revision.graph
    edges = dict(graph.edges)
    edges["exposes:payroll"] = Edge(
        id="exposes:payroll",
        type=EdgeType.EXPOSES,
        source_id="service:payroll",
        target_id="api:payroll",
    )
    edges["exposes:payroll-duplicate"] = Edge(
        id="exposes:payroll-duplicate",
        type=EdgeType.EXPOSES,
        source_id="service:other",
        target_id="api:payroll",
    )
    bound_revision = revision.model_copy(
        update={"graph": graph.model_copy(update={"edges": edges})}
    )

    with pytest.raises(ValueError, match="exactly one explicit EXPOSES service binding"):
        isr_to_plan(bound_revision)
