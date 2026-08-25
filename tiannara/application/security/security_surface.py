"""33.2 Security Attack Surface Contract."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class SurfaceType(str, Enum):
    HTTP_ENDPOINT = "HTTP_ENDPOINT"
    AUTH_FLOW = "AUTH_FLOW"
    AUTHORIZATION_BOUNDARY = "AUTHORIZATION_BOUNDARY"
    DB_INTERFACE = "DB_INTERFACE"
    EXTERNAL_NETWORK = "EXTERNAL_NETWORK"
    FILESYSTEM = "FILESYSTEM"
    PROCESS_EXECUTION = "PROCESS_EXECUTION"
    SERIALIZATION = "SERIALIZATION"
    SECRET = "SECRET"
    DEPENDENCY = "DEPENDENCY"
    MESSAGE_BROKER = "MESSAGE_BROKER"
    WEBSOCKET = "WEBSOCKET"
    CONTAINER = "CONTAINER"
    PRIVILEGED = "PRIVILEGED"


class Applicability(str, Enum):
    APPLICABLE = "APPLICABLE"
    NOT_APPLICABLE = "NOT_APPLICABLE"
    NOT_TESTED = "NOT_TESTED"


@dataclass(frozen=True)
class SecuritySurfaceElement:
    surface_id: str
    surface_type: SurfaceType
    source_ref: str
    artifact_ref: str
    isr_ref: str
    applicability: Applicability
    extraction_provenance: str
