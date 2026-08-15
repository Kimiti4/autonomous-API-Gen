"""
ISR Field Definitions — typed data attributes within entities.
Technology-neutral: no database column types, no ORM annotations.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, unique
from typing import Any, Optional


@unique
class FieldType(str, Enum):
    STRING = "string"
    TEXT = "text"
    INTEGER = "integer"
    FLOAT = "float"
    DECIMAL = "decimal"
    BOOLEAN = "boolean"
    DATE = "date"
    DATETIME = "datetime"
    TIME = "time"
    UUID = "uuid"
    EMAIL = "email"
    URL = "url"
    ENUM = "enum"
    JSON = "json"
    BINARY = "binary"
    ARRAY = "array"
    REFERENCE = "reference"

    def __str__(self) -> str:
        return self.value


@unique
class FieldCardinality(str, Enum):
    REQUIRED = "required"
    OPTIONAL = "optional"
    LIST = "list"

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True)
class FieldConstraint:
    name: str
    constraint_type: str
    parameters: dict[str, Any] = field(default_factory=dict)
    message: str = ""


@dataclass(frozen=True)
class Field:
    name: str
    field_type: FieldType
    cardinality: FieldCardinality = FieldCardinality.REQUIRED
    description: str = ""
    default_value: Optional[str] = None
    constraints: tuple[FieldConstraint, ...] = ()
    enum_values: tuple[str, ...] = ()
    reference_target: Optional[str] = None
    is_primary_key: bool = False
    is_indexed: bool = False
    metadata: dict[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.field_type == FieldType.ENUM and not self.enum_values:
            raise ValueError(f"Field '{self.name}' is ENUM but has no enum_values")
        if self.field_type == FieldType.REFERENCE and not self.reference_target:
            raise ValueError(f"Field '{self.name}' is REFERENCE but has no reference_target")