"""CompilationPlan — the technology-neutral intermediate representation."""
from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from isr.core.behavior import (
    ApiBehavior,
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


class Service(BaseModel):
    model_config = ConfigDict(frozen=True)
    id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    data_models: list[DataModel] = Field(default_factory=list)
    published_events: list[Event] = Field(default_factory=list)
    consumed_events: list[Event] = Field(default_factory=list)
    behavior: ServiceBehavior | None = None
    security_policies: list[SecurityPolicy] = Field(default_factory=list)


class ApiOperation(BaseModel):
    model_config = ConfigDict(frozen=True)
    id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    behavior: ApiBehavior | None = None
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


class Effect(BaseModel):
    model_config = ConfigDict(frozen=True)
    id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    behavior: EffectBehavior | None = None


class Invariant(BaseModel):
    model_config = ConfigDict(frozen=True)
    id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    behavior: InvariantSpec | None = None


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
    invariants: list[Invariant] = Field(default_factory=list)
    frontend_routes: list[FrontendRoute] = Field(default_factory=list)
    frontend_interactions: list[FrontendInteraction] = Field(default_factory=list)
