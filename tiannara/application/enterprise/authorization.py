"""Technology-neutral RBAC/ABAC authorization primitives.

The engine is deny-by-default, evaluates explicit deny policies before allow
policies, and can enforce tenant isolation as an independent invariant. It is
an authorization decision component, not an authentication mechanism.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Mapping, Sequence

from pydantic import BaseModel, ConfigDict, Field, model_validator


class AuthorizationEffect(str, Enum):
    ALLOW = "allow"
    DENY = "deny"


class AttributeScope(str, Enum):
    SUBJECT = "subject"
    RESOURCE = "resource"
    ENVIRONMENT = "environment"


class AttributeOperator(str, Enum):
    EQUALS = "equals"
    NOT_EQUALS = "not_equals"
    IN = "in"
    CONTAINS = "contains"
    EXISTS = "exists"


class AttributeCondition(BaseModel):
    """One typed ABAC predicate against a subject/resource/environment value."""
    model_config = ConfigDict(frozen=True)

    scope: AttributeScope
    attribute: str = Field(min_length=1)
    operator: AttributeOperator
    expected: Any = None


class AuthorizationPolicy(BaseModel):
    """A declarative allow/deny rule independent of any framework."""
    model_config = ConfigDict(frozen=True)

    policy_id: str = Field(min_length=1)
    effect: AuthorizationEffect
    actions: tuple[str, ...] = Field(min_length=1)
    resource_types: tuple[str, ...] = Field(min_length=1)
    subject_ids: tuple[str, ...] = ()
    required_roles: tuple[str, ...] = ()
    conditions: tuple[AttributeCondition, ...] = ()

    @model_validator(mode="after")
    def validate_matchers(self) -> "AuthorizationPolicy":
        for field_name in ("actions", "resource_types", "subject_ids", "required_roles"):
            values = getattr(self, field_name)
            if any(not value.strip() for value in values):
                raise ValueError(f"{field_name} must not contain blank values")
        return self


class AuthorizationRequest(BaseModel):
    """Facts supplied by the trusted request boundary to the policy engine."""
    model_config = ConfigDict(frozen=True)

    subject_id: str = Field(min_length=1)
    action: str = Field(min_length=1)
    resource_type: str = Field(min_length=1)
    resource_id: str = ""
    subject_roles: tuple[str, ...] = ()
    subject_attributes: dict[str, Any] = Field(default_factory=dict)
    resource_attributes: dict[str, Any] = Field(default_factory=dict)
    environment_attributes: dict[str, Any] = Field(default_factory=dict)
    tenant_id: str | None = None
    tenant_isolation_required: bool = False


class AuthorizationResult(BaseModel):
    """Auditable decision with the policy identities that influenced it."""
    model_config = ConfigDict(frozen=True)

    allowed: bool
    reason: str
    matched_policy_ids: tuple[str, ...] = ()
    decision_model: str = "deny_by_default_deny_overrides_v1"


@dataclass
class AuthzCheck:
    subject: str
    resource: str
    allowed: bool


def _read_attribute(attributes: Mapping[str, Any], path: str) -> tuple[bool, Any]:
    current: Any = attributes
    for part in path.split("."):
        if not isinstance(current, Mapping) or part not in current:
            return False, None
        current = current[part]
    return True, current


def _condition_matches(condition: AttributeCondition, request: AuthorizationRequest) -> bool:
    source = {
        AttributeScope.SUBJECT: request.subject_attributes,
        AttributeScope.RESOURCE: request.resource_attributes,
        AttributeScope.ENVIRONMENT: request.environment_attributes,
    }[condition.scope]
    exists, actual = _read_attribute(source, condition.attribute)

    if condition.operator is AttributeOperator.EXISTS:
        return exists
    # Missing attributes never satisfy equality, inequality, membership, or
    # containment. This prevents absence from accidentally granting access.
    if not exists:
        return False
    if condition.operator is AttributeOperator.EQUALS:
        return actual == condition.expected
    if condition.operator is AttributeOperator.NOT_EQUALS:
        return actual != condition.expected
    if condition.operator is AttributeOperator.IN:
        return isinstance(condition.expected, (tuple, list, set, frozenset)) and actual in condition.expected
    if condition.operator is AttributeOperator.CONTAINS:
        try:
            return condition.expected in actual
        except (TypeError, AttributeError):
            return False
    return False


def _matches(policy: AuthorizationPolicy, request: AuthorizationRequest) -> bool:
    if "*" not in policy.actions and request.action not in policy.actions:
        return False
    if "*" not in policy.resource_types and request.resource_type not in policy.resource_types:
        return False
    if policy.subject_ids and "*" not in policy.subject_ids and request.subject_id not in policy.subject_ids:
        return False
    if policy.required_roles and not set(policy.required_roles).intersection(request.subject_roles):
        return False
    return all(_condition_matches(condition, request) for condition in policy.conditions)


class AuthorizationEngine:
    """Evaluate policies with explicit-deny precedence and default deny."""

    def __init__(self, policies: Sequence[AuthorizationPolicy] = ()) -> None:
        ids = [policy.policy_id for policy in policies]
        if len(ids) != len(set(ids)):
            raise ValueError("Authorization policy IDs must be unique")
        self._policies = tuple(policies)

    @property
    def policies(self) -> tuple[AuthorizationPolicy, ...]:
        return self._policies

    def evaluate(self, request: AuthorizationRequest) -> AuthorizationResult:
        if request.tenant_isolation_required:
            resource_tenant = request.resource_attributes.get("tenant_id")
            if not request.tenant_id or not isinstance(resource_tenant, str) or not resource_tenant:
                return AuthorizationResult(
                    allowed=False,
                    reason="tenant isolation required but tenant identity is missing",
                )
            if resource_tenant != request.tenant_id:
                return AuthorizationResult(
                    allowed=False,
                    reason="resource belongs to a different tenant",
                )

        matched = [policy for policy in self._policies if _matches(policy, request)]
        denies = [policy for policy in matched if policy.effect is AuthorizationEffect.DENY]
        if denies:
            return AuthorizationResult(
                allowed=False,
                reason="explicit deny policy matched",
                matched_policy_ids=tuple(sorted(policy.policy_id for policy in denies)),
            )

        allows = [policy for policy in matched if policy.effect is AuthorizationEffect.ALLOW]
        if allows:
            return AuthorizationResult(
                allowed=True,
                reason="allow policy matched and no deny policy matched",
                matched_policy_ids=tuple(sorted(policy.policy_id for policy in allows)),
            )

        return AuthorizationResult(
            allowed=False,
            reason="no matching allow policy; default deny",
        )


def check_isolation(tenant_a: str, tenant_b: str, resource_tenant: str) -> bool:
    """Compatibility helper: a resource is isolated to tenant A, not tenant B."""
    return bool(tenant_a) and tenant_a == resource_tenant and tenant_a != tenant_b
