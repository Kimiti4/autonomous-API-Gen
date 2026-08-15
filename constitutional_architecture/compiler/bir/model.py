from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class BIRNodeType(str, Enum):
    HANDLER = "handler"
    ENTITY = "entity"
    SERVICE = "service"
    REPOSITORY = "repository"
    ROUTER = "router"
    CONFIG = "config"
    MIDDLEWARE = "middleware"
    EVENT_HANDLER = "event_handler"
    TEST = "test"


@dataclass(frozen=True)
class BIRNode:
    id: str
    node_type: BIRNodeType
    name: str
    attributes: dict[str, Any] = field(default_factory=dict)
    children: tuple[BIRNode, ...] = ()


@dataclass(frozen=True)
class BIRModule:
    id: str
    name: str
    nodes: tuple[BIRNode, ...] = ()


@dataclass(frozen=True)
class BIR:
    project_name: str
    modules: tuple[BIRModule, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)
