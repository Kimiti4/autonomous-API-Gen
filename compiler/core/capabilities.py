"""Fail-closed semantic capability declarations for compiler backends."""
from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, ConfigDict, Field

from compiler.core.plan import CompilationPlan


class SemanticFeature(str, Enum):
    TYPED_FIELDS = "typed_fields"
    DECIMAL_SHAPE = "decimal_shape"
    FIELD_CONSTRAINTS = "field_constraints"
    EXPRESSIONS = "expressions"
    BUSINESS_RULES = "business_rules"
    STATE_TRANSITIONS = "state_transitions"
    API_CONTRACTS = "api_contracts"
    AUTHORIZATION_POLICIES = "authorization_policies"
    EFFECT_SEMANTICS = "effect_semantics"
    CONSEQUENCE_SEMANTICS = "consequence_semantics"
    INVARIANTS = "invariants"
    TYPED_EVENTS = "typed_events"
    FRONTEND_ROUTES = "frontend_routes"
    FRONTEND_INTERACTIONS = "frontend_interactions"
    FRONTEND_AUTH = "frontend_auth"


class BackendCapabilities(BaseModel):
    """Declared implementation support; an empty set means structural-only."""
    model_config = ConfigDict(frozen=True)
    backend_id: str = Field(min_length=1)
    version: str = Field(min_length=1)
    supported_features: frozenset[SemanticFeature] = frozenset()


class UnsupportedSemanticsError(ValueError):
    """A plan asks for semantics that the selected backend cannot prove."""


def required_features(plan: CompilationPlan) -> frozenset[SemanticFeature]:
    required: set[SemanticFeature] = set()

    for data_model in plan.data_models:
        behavior = data_model.behavior
        if behavior is None:
            continue
        required.add(SemanticFeature.TYPED_FIELDS)
        if any(field.precision is not None or field.scale is not None for field in behavior.fields):
            required.add(SemanticFeature.DECIMAL_SHAPE)
        if any(field.constraints for field in behavior.fields):
            required.add(SemanticFeature.FIELD_CONSTRAINTS)
        if behavior.invariants:
            required.update({SemanticFeature.INVARIANTS, SemanticFeature.EXPRESSIONS})

    for event in plan.events:
        if event.behavior is not None and event.behavior.fields:
            required.update({SemanticFeature.TYPED_EVENTS, SemanticFeature.TYPED_FIELDS})

    for service in plan.services:
        behavior = service.behavior
        if behavior is not None:
            if behavior.rules:
                required.update({SemanticFeature.BUSINESS_RULES, SemanticFeature.EXPRESSIONS})
            if behavior.transitions:
                required.add(SemanticFeature.STATE_TRANSITIONS)
                if any(transition.guard is not None for transition in behavior.transitions):
                    required.add(SemanticFeature.EXPRESSIONS)
        if any(policy.behavior is not None for policy in service.security_policies):
            required.add(SemanticFeature.AUTHORIZATION_POLICIES)

    for api in plan.apis:
        if api.behavior is not None:
            required.add(SemanticFeature.API_CONTRACTS)
        # A policy bound to an operation is an authorization obligation in its
        # own right. It must not disappear from capability checks just because
        # the policy carries no typed behavior, and it must not disappear
        # because the operation has no behavior payload of its own.
        if api.security_policies or (
            api.behavior is not None and api.behavior.authorization_policy_ids
        ):
            required.add(SemanticFeature.AUTHORIZATION_POLICIES)

    for policy in plan.security:
        if policy.behavior is not None:
            required.add(SemanticFeature.AUTHORIZATION_POLICIES)

    for effect in plan.effects:
        if effect.behavior is not None:
            required.add(SemanticFeature.EFFECT_SEMANTICS)
    # A source-bound effect edge is itself an execution obligation even when
    # the target effect has only legacy structural properties.
    if plan.effect_bindings:
        required.add(SemanticFeature.EFFECT_SEMANTICS)
    if plan.consequences:
        required.add(SemanticFeature.CONSEQUENCE_SEMANTICS)

    for invariant in plan.invariants:
        if invariant.behavior is not None:
            required.update({SemanticFeature.INVARIANTS, SemanticFeature.EXPRESSIONS})

    return frozenset(required)


def required_frontend_features(plan: CompilationPlan) -> frozenset[SemanticFeature]:
    """Return only the frontend compiler obligations in a shared plan."""
    required: set[SemanticFeature] = set()
    if plan.frontend_routes:
        required.add(SemanticFeature.FRONTEND_ROUTES)
    if plan.frontend_interactions:
        required.add(SemanticFeature.FRONTEND_INTERACTIONS)
    if any(route.api_operations for route in plan.frontend_routes):
        required.add(SemanticFeature.API_CONTRACTS)
    if any(route.behavior is not None and route.behavior.requires_auth for route in plan.frontend_routes):
        required.add(SemanticFeature.FRONTEND_AUTH)
    return frozenset(required)


def assert_frontend_plan_supported(
    plan: CompilationPlan,
    capabilities: BackendCapabilities,
) -> None:
    unsupported = sorted(
        feature.value
        for feature in required_frontend_features(plan) - capabilities.supported_features
    )
    if unsupported:
        auth_hint = (
            "; no authentication flow is implemented for frontend_auth"
            if SemanticFeature.FRONTEND_AUTH.value in unsupported
            else ""
        )
        raise UnsupportedSemanticsError(
            f"Frontend backend {capabilities.backend_id}@{capabilities.version} cannot compile "
            f"declared ISR semantics; unsupported features: {', '.join(unsupported)}{auth_hint}"
        )


def assert_plan_supported(plan: CompilationPlan, capabilities: BackendCapabilities) -> None:
    unsupported = sorted(
        feature.value
        for feature in required_features(plan) - capabilities.supported_features
    )
    if unsupported:
        raise UnsupportedSemanticsError(
            f"Backend {capabilities.backend_id}@{capabilities.version} cannot compile "
            f"declared ISR semantics; unsupported features: {', '.join(unsupported)}"
        )


def structural_only(backend_id: str, version: str) -> BackendCapabilities:
    """Honest default until runtime evidence justifies feature promotion."""
    return BackendCapabilities(backend_id=backend_id, version=version)
