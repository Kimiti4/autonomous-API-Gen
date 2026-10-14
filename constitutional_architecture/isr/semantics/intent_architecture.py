"""First-class identity and gate state for a typed architecture projection."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class IntentArchitectureReference:
    system_model_sha256: str
    projection_complete: bool
    projection_blockers: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.system_model_sha256:
            raise ValueError("typed architecture projection requires a SystemModel hash")
        if self.projection_complete and self.projection_blockers:
            raise ValueError("a complete architecture projection cannot contain blockers")
        if not self.projection_complete and not self.projection_blockers:
            raise ValueError("an incomplete architecture projection must record blockers")
