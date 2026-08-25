"""CompilationPlan — the technology-neutral intermediate representation."""
from __future__ import annotations
from pydantic import BaseModel, ConfigDict, Field


class DataModel(BaseModel):
    model_config = ConfigDict(frozen=True)
    id: str = Field(min_length=1)
    entity_name: str = Field(min_length=1)


class Event(BaseModel):
    model_config = ConfigDict(frozen=True)
    id: str = Field(min_length=1)
    name: str = Field(min_length=1)


class SecurityPolicy(BaseModel):
    model_config = ConfigDict(frozen=True)
    policy_id: str = Field(min_length=1)


class Service(BaseModel):
    model_config = ConfigDict(frozen=True)
    id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    data_models: list[DataModel] = Field(default_factory=list)
    published_events: list[Event] = Field(default_factory=list)
    consumed_events: list[Event] = Field(default_factory=list)


class CompilationPlan(BaseModel):
    """Deterministic compilation plan — the tech-neutral IR between
    ISR lowering and backend emission."""
    model_config = ConfigDict(frozen=True)

    plan_id: str = Field(min_length=1)
    isr_id: str = Field(min_length=1)
    services: list[Service] = Field(default_factory=list)
    security: list[SecurityPolicy] = Field(default_factory=list)
