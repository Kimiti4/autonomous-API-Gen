"""
ISR Interface Model — API contracts (REST, gRPC, GraphQL, event subscriptions).
Technology-neutral: no framework routers, no HTTP libraries.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, unique
from typing import Optional

from constitutional_architecture.isr.model.fields import Field


@unique
class InterfaceType(str, Enum):
    REST = "rest"
    GRAPHQL = "graphql"
    GRPC = "grpc"
    EVENT_SUBSCRIPTION = "event_subscription"
    WEBSOCKET = "websocket"
    INTERNAL = "internal"


@unique
class HttpMethod(str, Enum):
    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    PATCH = "PATCH"
    DELETE = "DELETE"
    HEAD = "HEAD"
    OPTIONS = "OPTIONS"


@dataclass(frozen=True)
class Endpoint:
    id: str
    name: str
    path: str = ""
    method: HttpMethod = HttpMethod.GET
    description: str = ""
    input_schema: tuple[Field, ...] = ()
    output_schema: tuple[Field, ...] = ()
    required_permissions: tuple[str, ...] = ()
    is_public: bool = False
    rate_limit: Optional[int] = None
    metadata: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class Interface:
    id: str
    name: str
    interface_type: InterfaceType = InterfaceType.REST
    description: str = ""
    version: str = "1.0"
    endpoints: tuple[Endpoint, ...] = ()
    secured_by_policy_id: Optional[str] = None
    is_internal: bool = False
    metadata: dict[str, str] = field(default_factory=dict)