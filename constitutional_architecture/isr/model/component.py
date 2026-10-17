"""First-class technology-neutral component identity in the constitutional ISR."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Component:
    component_id: str
    service_id: str
    name: str
    responsibility: str = ""
    kind: str = "application_service"

    def __post_init__(self) -> None:
        if not self.component_id or not self.service_id or not self.name or not self.kind:
            raise ValueError("component identity, owning service, name and kind are required")
