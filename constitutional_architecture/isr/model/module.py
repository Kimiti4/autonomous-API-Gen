"""
ISR Module Model — bounded contexts owning entities, services, and interfaces.
Technology-neutral: no package structure, no deployment unit.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from constitutional_architecture.isr.model.entity import Entity
from constitutional_architecture.isr.model.event import Event
from constitutional_architecture.isr.model.interface import Interface
from constitutional_architecture.isr.model.policy import Policy
from constitutional_architecture.isr.model.service import Service
from constitutional_architecture.isr.model.workflow import Workflow
from constitutional_architecture.isr.semantics.temporal import TemporalConstraint


@dataclass(frozen=True)
class Module:
    id: str
    name: str
    description: str = ""
    entities: tuple[Entity, ...] = ()
    services: tuple[Service, ...] = ()
    workflows: tuple[Workflow, ...] = ()
    policies: tuple[Policy, ...] = ()
    interfaces: tuple[Interface, ...] = ()
    events: tuple[Event, ...] = ()
    dependencies: tuple[str, ...] = ()
    metadata: dict[str, str] = field(default_factory=dict)
    temporal_constraints: tuple[TemporalConstraint, ...] = ()

    def get_entity(self, entity_id: str) -> Optional[Entity]:
        for e in self.entities:
            if e.id == entity_id:
                return e
        return None

    def get_service(self, service_id: str) -> Optional[Service]:
        for s in self.services:
            if s.id == service_id:
                return s
        return None