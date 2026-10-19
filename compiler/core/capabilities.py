"""Fail-closed semantic capability declarations for compiler backends."""
from __future__ import annotations

from enum import Enum
from typing import Iterable

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
    for service in plan.services:
        if service.behavior is not None:
            if service.behavior.rules:
                required.add(SemanticFeature.BUSINESS_RULES)
                required.add(SemanticFeature.EXPRESSIONS)
            if service.behavior.transitions:
                required.add(SemanticFeature.STATE_TRANSITIONS)
                if any(t.guard is not None for t in service.behavior.transitions):
                    required.add(SemanticFeature.EXPRESSIONS)
        for model in service.data_models:
            if model.behavior is not None:
                required.add(SemanticFeature.TYPED_FIELDS)
                if any(field.constraints for field in model.behavior.fields):
                    required.add(SemanticFeature.FIELD_CONSTRAINTS)
                if any(model.invariants for model in [model.behavior]):
                    required.add(SemanticFeature.INVARIANTS)
                    required.add(SemanticFeature.EXPRESSIONS)
        for event in service.published_events + service.consumed_events:
            if event.behavior is not None and event.behavior.fields:
                required.add(SemanticFeature.TYPED_EVENTS)
                required.add(SemanticFeature.TYPED_FIELDS)
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
            required.add(SemanticFeature.INVARIANTS)
            required.add(SemanticFeature.EXPRESSIONS)
    return frozenset(required)


def assert_plan_supported(plan: CompilationPlan, capabilities: BackendCapabilities) -> None:
    required = required_features(plan)
    unsupported = sorted(feature.value for feature in required - capabilities.supported_features)
    if unsupported:
        raise UnsupportedSemanticsError(
            f"Backend {capabilities.backend_id}@{capabilities.version} cannot compile "
            f"declared ISR semantics; unsupported features: {', '.join(unsupported)}"
        )


def structural_only(backend_id: str, version: str) -> BackendCapabilities:
    """Honest default until runtime evidence justifies feature promotion."""
    return BackendCapabilities(backend_id=backend_id, version=version)
