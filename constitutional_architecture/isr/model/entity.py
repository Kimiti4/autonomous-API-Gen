"""
ISR Entity Model — domain objects with fields, constraints, and relationships.
Technology-neutral: no ORM models, no database tables.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from constitutional_architecture.isr.model.constraints import Constraint
from constitutional_architecture.isr.model.fields import Field


@dataclass(frozen=True)
class Relationship:
    target_entity_id: str
    relationship_type: str = "one_to_many"
    field_name: str = ""
    inverse_field_name: str = ""
    cascade_delete: bool = False
    description: str = ""


@dataclass(frozen=True)
class Entity:
    id: str
    name: str
    description: str = ""
    fields: tuple[Field, ...] = ()
    relationships: tuple[Relationship, ...] = ()
    constraints: tuple[Constraint, ...] = ()
    is_aggregate_root: bool = False
    is_value_object: bool = False
    metadata: dict[str, str] = field(default_factory=dict)

    @property
    def primary_key_fields(self) -> tuple[Field, ...]:
        return tuple(f for f in self.fields if f.is_primary_key)

    def get_field(self, name: str) -> Optional[Field]:
        for f in self.fields:
            if f.name == name:
                return f
        return None