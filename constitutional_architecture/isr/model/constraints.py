"""
ISR Constraint Definitions — hard architectural rules or boundaries.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, unique
from typing import Any


@unique
class ConstraintScope(str, Enum):
    SYSTEM = "system"
    MODULE = "module"
    ENTITY = "entity"
    SERVICE = "service"
    FIELD = "field"
    INTERFACE = "interface"
    GLOBAL = "global"


@unique
class ConstraintSeverity(str, Enum):
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


@dataclass(frozen=True)
class Constraint:
    id: str
    name: str
    scope: ConstraintScope
    severity: ConstraintSeverity = ConstraintSeverity.ERROR
    description: str = ""
    rule_type: str = ""
    parameters: dict[str, Any] = field(default_factory=dict)
    target_node_ids: tuple[str, ...] = ()
    message: str = ""