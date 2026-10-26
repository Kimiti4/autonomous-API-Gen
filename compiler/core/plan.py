"""CompilationPlan — the technology-neutral intermediate representation."""
from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from isr.core.behavior import (
    ApiBehavior,
    ConsequenceBehavior,
    DataModelBehavior,
    EffectBehavior,
    EventBehavior,
    FrontendInteractionBehavior,
    FrontendRouteBehavior,
    InvariantSpec,
    SecurityBehavior,
    ServiceBehavior,
)


class DataModel(BaseModel):
    model_config = ConfigDict(frozen=True)
    id: str = Field(min_length=1)
    entity_name: str = Field(min_length=1)
    behavior: DataModelBehavior | None = None


class Event(BaseModel):
    model_config = ConfigDict(frozen=True)
    id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    behavior: EventBehavior | None = None


class SecurityPolicy(BaseModel):
    model_config = ConfigDict(frozen=True)
    policy_id: str = Field(min_length=1)
    behavior: SecurityBehavior | None = None


class Effect(BaseModel):
    model_config = ConfigDict(frozen=True)
    id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    behavior: EffectBehavior | None = None
    # Preserve legacy/source-declared policy fields until a typed executable
    # contract can consume them; capability gates must not ignore this payload.
    declared_policy: dict[str, Any] = Field(default_factory=dict)
    # Policies that govern this effect. They are not service route policies.
    security_policies: list[SecurityPolicy] = Field(default_factory=list)


class Service(BaseModel):
    model_config = ConfigDict(frozen=True)
    id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    data_models: list[DataModel] = Field(default_factory=list)
    published_events: list[Event] = Field(default_factory=list)
    consumed_events: list[Event] = Field(default_factory=list)
    effects: list[Effect] = Field(default_factory=list)
    behavior: ServiceBehavior | None = None
    security_policies: list[SecurityPolicy] = Field(default_factory=list)


class ApiOperation(BaseModel):
    model_config = ConfigDict(frozen=True)
    id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    behavior: ApiBehavior | None = None
    # Explicit ISR EXPOSES relation. Never infer an owning service from names
    # or request fields; emitters need this binding to implement side effects.
    service_id: str | None = None
    security_policies: list[SecurityPolicy] = Field(default_factory=list)


class FrontendInteraction(BaseModel):
    model_config = ConfigDict(frozen=True)
    id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    behavior: FrontendInteractionBehavior | None = None
    target_api_operation: ApiOperation | None = None


class FrontendRoute(BaseModel):
    model_config = ConfigDict(frozen=True)
    id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    behavior: FrontendRouteBehavior | None = None
    api_operations: list[ApiOperation] = Field(default_factory=list)
    interactions: list[FrontendInteraction] = Field(default_factory=list)


class Invariant(BaseModel):
    model_config = ConfigDict(frozen=True)
    id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    behavior: InvariantSpec | None = None


class Consequence(BaseModel):
    """Observable consequence preserved from a first-class ISR node."""
    model_config = ConfigDict(frozen=True)
    id: str = Field(min_length=1)
    behavior: ConsequenceBehavior
    # IDs reached by explicit ISR CONSEQUENCE_OF edges; never inferred by name.
    related_node_ids: tuple[str, ...] = Field(min_length=1)


class EffectBinding(BaseModel):
    """Source-bound CAUSES_EFFECT edge, regardless of source node kind."""
    model_config = ConfigDict(frozen=True)
    edge_id: str = Field(min_length=1)
    source_id: str = Field(min_length=1)
    effect_id: str = Field(min_length=1)


class CompilationPlan(BaseModel):
    """Deterministic, technology-neutral IR between ISR lowering and emitters.

    Behavioral payloads are carried as typed models, not flattened to labels.
    Backends must still prove that they implement each populated contract.
    """
    model_config = ConfigDict(frozen=True)

    plan_id: str = Field(min_length=1)
    isr_id: str = Field(min_length=1)
    services: list[Service] = Field(default_factory=list)
    data_models: list[DataModel] = Field(default_factory=list)
    events: list[Event] = Field(default_factory=list)
    security: list[SecurityPolicy] = Field(default_factory=list)
    apis: list[ApiOperation] = Field(default_factory=list)
    effects: list[Effect] = Field(default_factory=list)
    effect_bindings: list[EffectBinding] = Field(default_factory=list)
    consequences: list[Consequence] = Field(default_factory=list)
    invariants: list[Invariant] = Field(default_factory=list)
    frontend_routes: list[FrontendRoute] = Field(default_factory=list)
    frontend_interactions: list[FrontendInteraction] = Field(default_factory=list)
    # Content hash of the ISR revision this plan was lowered from.
    # Hand-built plans leave it empty; they are not a source candidate.
    obligation_revision: str | None = None
