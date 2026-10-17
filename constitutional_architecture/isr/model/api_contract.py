"""First-class API contract without guessed transport paths or methods."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ApiOperationContract:
    name: str
    description: str = ""
    semantics: str = "query"
    idempotent: bool = False

    def __post_init__(self) -> None:
        if not self.name or self.semantics not in {"command", "query"}:
            raise ValueError("API operation requires a name and recognized semantics")


@dataclass(frozen=True)
class ApiContract:
    api_id: str
    name: str
    provider_service_id: str
    consumer_service_ids: tuple[str, ...] = ()
    interaction_style: str = "request_response"
    operations: tuple[ApiOperationContract, ...] = ()

    def __post_init__(self) -> None:
        if not self.api_id or not self.name or not self.provider_service_id:
            raise ValueError("API identity and provider service are required")
        if self.interaction_style not in {
            "request_response", "event_driven", "batch", "streaming"
        }:
            raise ValueError("unsupported API interaction style")
