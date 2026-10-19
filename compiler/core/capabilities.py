"""Fail-closed semantic capability declarations for compiler backends."""
from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, ConfigDict, Field

from compiler.core.plan import CompilationPlan


class SemanticFeature(str, Enum):
    TYPED_FIELDS = "typed_fields"
    FIELD_CONSTRAINTS = "field_constraints"
    EXPRESSIONS = "expressions"
    BUSINESS_RULES = "business_rules"
    STATE_TRANSITIONS = "state_transitions"
    API_CONTRACTS = "api_contracts"
    AUTHORIZATION_POLICIES = "authorization_policies"
    EFFECT_SEMANTICS = "effect_semantics"
    INVARIANTS = "invariants"
    TYPED_EVENTS = "typed_events"


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
        if service.security_policies:
            required.add(SemanticFeature.AUTHORIZATION_POLICIES)

    for api in plan.apis:
        if api.behavior is not None:
            required.add(SemanticFeature.API_CONTRACTS)
            if api.behavior.authorization_policy_ids or api.security_policies:
                required.add(SemanticFeature.AUTHORIZATION_POLICIES)

    for policy in plan.security:
        if policy.behavior is not None:
            required.add(SemanticFeature.AUTHORIZATION_POLICIES)

    for effect in plan.effects:
        if effect.behavior is not None:
            required.add(SemanticFeature.EFFECT_SEMANTICS)

    for invariant in plan.invariants:
        if invariant.behavior is not None:
            required.update({SemanticFeature.INVARIANTS, SemanticFeature.EXPRESSIONS})

    return frozenset(required)


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
