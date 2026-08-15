"""
ISR Event Model — domain events with schema and routing information.
Technology-neutral: no Kafka topics, no RabbitMQ queues.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, unique
from typing import Optional

from constitutional_architecture.isr.model.fields import Field


@unique
class EventPattern(str, Enum):
    FIRE_AND_FORGET = "fire_and_forget"
    PUBLISH_SUBSCRIBE = "publish_subscribe"
    POINT_TO_POINT = "point_to_point"
    REQUEST_REPLY = "request_reply"


@unique
class EventGuarantee(str, Enum):
    AT_MOST_ONCE = "at_most_once"
    AT_LEAST_ONCE = "at_least_once"
    EXACTLY_ONCE = "exactly_once"


@dataclass(frozen=True)
class Event:
    id: str
    name: str
    description: str = ""
    schema: tuple[Field, ...] = ()
    pattern: EventPattern = EventPattern.PUBLISH_SUBSCRIBE
    guarantee: EventGuarantee = EventGuarantee.AT_LEAST_ONCE
    ordering_required: bool = False
    ttl_seconds: Optional[int] = None
    metadata: dict[str, str] = field(default_factory=dict)