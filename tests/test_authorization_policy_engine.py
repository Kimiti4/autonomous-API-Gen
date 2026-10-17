"""Security regression tests for the framework-neutral authorization engine."""
import pytest

from tiannara.application.enterprise.authorization import (
    AttributeCondition,
    AttributeOperator,
    AttributeScope,
    AuthorizationEffect,
    AuthorizationEngine,
    AuthorizationPolicy,
    AuthorizationRequest,
    check_isolation,
)


def _policy(policy_id, effect=AuthorizationEffect.ALLOW, **kwargs):
    return AuthorizationPolicy(
        policy_id=policy_id,
        effect=effect,
        actions=kwargs.pop("actions", ("read",)),
        resource_types=kwargs.pop("resource_types", ("document",)),
        **kwargs,
    )


def _request(**kwargs):
    return AuthorizationRequest(
        subject_id=kwargs.pop("subject_id", "user-1"),
        action=kwargs.pop("action", "read"),
        resource_type=kwargs.pop("resource_type", "document"),
        **kwargs,
    )


def test_authorization_defaults_to_deny():
    result = AuthorizationEngine().evaluate(_request())

    assert not result.allowed
    assert result.reason == "no matching allow policy; default deny"


def test_rbac_policy_allows_matching_role_only():
    engine = AuthorizationEngine([_policy("reader", required_roles=("reader",))])

    allowed = engine.evaluate(_request(subject_roles=("reader",)))
    denied = engine.evaluate(_request(subject_roles=("guest",)))

    assert allowed.allowed
    assert allowed.matched_policy_ids == ("reader",)
    assert not denied.allowed


def test_explicit_deny_overrides_matching_allow():
    engine = AuthorizationEngine([
        _policy("allow-reader", required_roles=("reader",)),
        _policy("deny-suspended", AuthorizationEffect.DENY, subject_ids=("user-1",)),
    ])

    result = engine.evaluate(_request(subject_roles=("reader",)))

    assert not result.allowed
    assert result.matched_policy_ids == ("deny-suspended",)
    assert "explicit deny" in result.reason


def test_abac_conditions_support_nested_resource_attributes():
    engine = AuthorizationEngine([
        _policy(
            "department-document",
            required_roles=("staff",),
            conditions=(
                AttributeCondition(
                    scope=AttributeScope.RESOURCE,
                    attribute="classification.level",
                    operator=AttributeOperator.EQUALS,
                    expected="internal",
                ),
                AttributeCondition(
                    scope=AttributeScope.SUBJECT,
                    attribute="department",
                    operator=AttributeOperator.EQUALS,
                    expected="finance",
                ),
            ),
        )
    ])

    request = _request(
        subject_roles=("staff",),
        subject_attributes={"department": "finance"},
        resource_attributes={"classification": {"level": "internal"}},
    )
    wrong_department = _request(
        subject_roles=("staff",),
        subject_attributes={"department": "programs"},
        resource_attributes={"classification": {"level": "internal"}},
    )

    assert engine.evaluate(request).allowed
    assert not engine.evaluate(wrong_department).allowed


def test_missing_abac_attribute_does_not_grant_access_even_for_not_equals():
    engine = AuthorizationEngine([
        _policy(
            "attribute-guard",
            conditions=(
                AttributeCondition(
                    scope=AttributeScope.SUBJECT,
                    attribute="clearance",
                    operator=AttributeOperator.NOT_EQUALS,
                    expected="revoked",
                ),
            ),
        )
    ])

    assert not engine.evaluate(_request()).allowed


def test_tenant_isolation_is_an_independent_mandatory_guard():
    engine = AuthorizationEngine([_policy("broad-allow", actions=("*",), resource_types=("*",))])

    cross_tenant = engine.evaluate(_request(
        tenant_id="tenant-a",
        tenant_isolation_required=True,
        resource_attributes={"tenant_id": "tenant-b"},
    ))
    missing_tenant = engine.evaluate(_request(
        tenant_id="tenant-a",
        tenant_isolation_required=True,
        resource_attributes={},
    ))
    same_tenant = engine.evaluate(_request(
        tenant_id="tenant-a",
        tenant_isolation_required=True,
        resource_attributes={"tenant_id": "tenant-a"},
    ))

    assert not cross_tenant.allowed
    assert not missing_tenant.allowed
    assert same_tenant.allowed


def test_duplicate_policy_ids_are_rejected():
    with pytest.raises(ValueError, match="must be unique"):
        AuthorizationEngine([
            _policy("same-id"),
            _policy("same-id", AuthorizationEffect.DENY),
        ])


def test_legacy_tenant_isolation_helper_remains_available():
    assert check_isolation("tenant-a", "tenant-b", "tenant-a")
    assert not check_isolation("tenant-a", "tenant-b", "tenant-b")
    assert not check_isolation("", "tenant-b", "")
